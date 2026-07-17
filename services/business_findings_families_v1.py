# -*- coding: utf-8 -*-
"""
Deterministic finding family evaluators for Business Findings Engine V1.

Each evaluator returns 0..N BusinessFindingV1 dicts (pre-finalize).
No AI. No guessing confirmed causes without evidence.
"""
from __future__ import annotations

from typing import Any, Iterable

from services.business_findings_contract_v1 import (
    CONFIDENCE_HIGH,
    CONFIDENCE_INSUFFICIENT,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    REC_ACT_NOW,
    REC_INSUFFICIENT,
    REC_INVESTIGATE,
    REC_MONITOR,
    REC_TEST,
    SCOPE_HESITATION_REASON,
    SCOPE_PRODUCT,
    SCOPE_RECOVERY_CHANNEL,
    SCOPE_STORE,
    STATUS_CONFIRMED,
    STATUS_CONFLICTING,
    STATUS_EMERGING,
    STATUS_INSUFFICIENT,
    SURFACE_CARTS,
    SURFACE_CUSTOMERS,
    SURFACE_HOME,
    SURFACE_KNOWLEDGE,
    SURFACE_PRODUCTS,
    SURFACE_WHATSAPP,
    TYPE_DOMINANT_HESITATION,
    TYPE_HESITATION_RESOLUTION,
    TYPE_HIGH_INTEREST_LOW_PURCHASE,
    TYPE_INSUFFICIENT_OR_CONFLICTING,
    TYPE_LOW_PRODUCT_INTEREST,
    TYPE_MISSING_CONTACT_BLOCKS,
    TYPE_RECOVERY_CHANNEL_EFFECTIVENESS,
    TYPE_REPEATED_INTEREST,
    TYPE_RETURN_WITHOUT_PURCHASE,
    TYPE_TRAFFIC_VS_CONVERSION,
    TYPE_WHATSAPP_TEST_CANDIDATE,
    empty_finding,
    reason_label_ar,
)
from services.business_findings_evidence_v1 import EvidenceBundle

# Governed thresholds (deterministic V1)
MIN_HESITATION_TOTAL = 8
MIN_DOMINANT_COUNT = 5
MIN_DOMINANT_SHARE = 0.40
MIN_PRODUCT_ATC = 8
MAX_CONVERSION_WEAK = 0.12
MIN_PEER_ATC = 8
LOW_INTEREST_RATIO = 0.25
MIN_WA_SENT = 10
MIN_WA_RETURN = 5
MAX_WA_PURCHASE_RATE = 0.25
MIN_RETURN_SAMPLE = 8
MIN_REPEAT_ATC = 6


def _conf(sample: int, *, strong: int = 20, medium: int = 10) -> tuple[str, float]:
    if sample >= strong:
        return CONFIDENCE_HIGH, min(0.95, 0.55 + sample / 100.0)
    if sample >= medium:
        return CONFIDENCE_MEDIUM, min(0.75, 0.40 + sample / 80.0)
    if sample > 0:
        return CONFIDENCE_LOW, max(0.15, sample / 40.0)
    return CONFIDENCE_INSUFFICIENT, 0.0


def _base(ev: EvidenceBundle, finding_type: str, finding_id: str) -> dict[str, Any]:
    f = empty_finding(
        finding_id=finding_id,
        store_slug=ev.store_slug,
        finding_type=finding_type,
    )
    f["observed_period"] = dict(ev.observed_period or {})
    f["evidence_refs"] = list(ev.source_tables or [])
    return f


def evaluate_missing_contact_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    """Deduped commercial contact blocker (aligns with CIL — one finding only)."""
    if int(ev.no_phone_total or 0) <= 0:
        return []
    count = int(ev.no_phone_total)
    conf_l, conf_s = _conf(count, strong=20, medium=8)
    f = _base(ev, TYPE_MISSING_CONTACT_BLOCKS, f"finding:{TYPE_MISSING_CONTACT_BLOCKS}")
    f.update(
        {
            "finding_scope": SCOPE_STORE,
            "scope_reference": "no_phone_total",
            "title": "نقص بيانات التواصل يعيق استرجاع جزء مهم من السلال",
            "merchant_summary": (
                f"يوجد حالياً {count} سلة لا يمكن بدء استرجاعها لأن وسيلة التواصل غير متوفرة."
            ),
            "commercial_meaning": (
                "كل سلة بلا تواصل صالح تبقى خارج مسار واتساب، فيتأجل استرجاع الإيراد."
            ),
            "evidence_summary": (
                f"{count} سلة نشطة بلا رقم صالح"
                + (f" من أصل {ev.active_carts}" if ev.active_carts else "")
                + "."
            ),
            "sample_size": count,
            "confidence_level": conf_l,
            "confidence_score": conf_s,
            "business_impact": "حماية إيراد معلّق يعتمد على إكمال بيانات التواصل.",
            "recommended_direction": (
                "حسّن التقاط رقم العميل قبل مغادرة المتجر، وراجع السلال المحظورة."
            ),
            "recommendation_type": REC_ACT_NOW,
            "status": STATUS_CONFIRMED if count >= 8 else STATUS_EMERGING,
            "authoritative_surface": SURFACE_CARTS,
            "home_eligible": True,
            "family_key": "contact_blocker",
            "is_confirmed_cause": True,
        }
    )
    return [f]


def evaluate_dominant_hesitation_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    total = int(ev.hesitation_total or 0)
    dist = dict(ev.hesitation_distribution or {})
    if total < MIN_HESITATION_TOTAL or not dist:
        f = _base(
            ev,
            TYPE_DOMINANT_HESITATION,
            f"finding:{TYPE_DOMINANT_HESITATION}:insufficient",
        )
        f.update(
            {
                "title": "لا يكفي دليل بعد لتحديد سبب التردد الأبرز",
                "merchant_summary": (
                    f"عدد أسباب التردد المسجّلة ({total}) أقل من الحد الآمن لاستنتاج موثوق."
                ),
                "commercial_meaning": (
                    "إصدار توصية تجارية الآن قد يوجّه قراراتك بناءً على عينة غير كافية."
                ),
                "evidence_summary": f"hesitation_total={total}",
                "sample_size": total,
                "status": STATUS_INSUFFICIENT,
                "recommendation_type": REC_INSUFFICIENT,
                "recommended_direction": "استمر في جمع أسباب التردد عبر التفاعل مع العملاء.",
                "authoritative_surface": SURFACE_KNOWLEDGE,
                "home_eligible": False,
                "family_key": "hesitation",
            }
        )
        return [f]

    top_reason, top_count = max(dist.items(), key=lambda kv: kv[1])
    share = top_count / max(total, 1)
    if top_count < MIN_DOMINANT_COUNT or share < MIN_DOMINANT_SHARE:
        f = _base(
            ev,
            TYPE_DOMINANT_HESITATION,
            f"finding:{TYPE_DOMINANT_HESITATION}:not_dominant",
        )
        f.update(
            {
                "title": "أسباب التردد موزّعة — لا سبب مهيمن بوضوح بعد",
                "merchant_summary": (
                    "لا يظهر سبب واحد يهيمن تجارياً بما يكفي لاعتباره الأولوية."
                ),
                "commercial_meaning": (
                    "التركيز على سبب واحد الآن قد يتجاهل تردداً موزّعاً بين عدة عوامل."
                ),
                "evidence_summary": f"top={top_reason}:{top_count}/{total} share={share:.0%}",
                "sample_size": total,
                "status": STATUS_EMERGING,
                "recommendation_type": REC_MONITOR,
                "recommended_direction": "راقب التوزيع لأيام إضافية قبل تغيير العرض.",
                "confidence_level": CONFIDENCE_LOW,
                "confidence_score": 0.35,
                "authoritative_surface": SURFACE_KNOWLEDGE,
                "home_eligible": True,
                "family_key": "hesitation",
            }
        )
        return [f]

    label = reason_label_ar(top_reason)
    conf_l, conf_s = _conf(total)
    # Category hint from product mapping if concentrated
    scope = SCOPE_HESITATION_REASON
    scope_ref = top_reason
    cat_note = ""
    by_prod = ev.hesitation_by_product or {}
    if by_prod:
        best_pid, best_map = max(
            by_prod.items(), key=lambda kv: int((kv[1] or {}).get(top_reason, 0))
        )
        local = int((best_map or {}).get(top_reason, 0))
        if local >= 5 and local / max(top_count, 1) >= 0.5:
            scope = SCOPE_PRODUCT
            scope_ref = best_pid
            cat_note = " ضمن مجموعة منتجات مرتبطة بهذا السبب"

    f = _base(ev, TYPE_DOMINANT_HESITATION, f"finding:{TYPE_DOMINANT_HESITATION}:{top_reason}")
    f.update(
        {
            "finding_scope": scope,
            "scope_reference": scope_ref,
            "title": f"{label} هو أبرز سبب للتردّد حالياً{cat_note}",
            "merchant_summary": (
                f"{label} يتكرر في {top_count} من أصل {total} سبب مسجّل "
                f"({share:.0%}) — وهو الأعلى بوضوح أمام بقية الأسباب."
            ),
            "commercial_meaning": (
                "هذا النمط يشير إلى عائق شراء متكرر يؤثر على جزء كبير من السلال المترددة."
            ),
            "evidence_summary": (
                f"distribution={dist}; top={top_reason}:{top_count}; "
                f"compared_against={sorted(dist.keys())}"
            ),
            "sample_size": total,
            "confidence_level": conf_l,
            "confidence_score": conf_s,
            "business_impact": "معالجة هذا السبب قد تفتح مسار شراء لعدد أكبر من السلال المترددة.",
            "recommended_direction": (
                "راجع وضوح التكلفة/العرض المرتبط بهذا السبب، واختبر تحسيناً واحداً وقِس الأثر."
            ),
            "recommendation_type": REC_INVESTIGATE,
            "status": STATUS_CONFIRMED,
            "authoritative_surface": SURFACE_KNOWLEDGE,
            "home_eligible": True,
            "family_key": "hesitation",
            "is_confirmed_cause": False,  # dominant pattern ≠ proven root cause fix
        }
    )
    return [f]


def evaluate_high_interest_low_purchase_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    products = dict(ev.products or {})
    if len(products) < 2:
        return []
    store_adds = sum(int(p.get("add_to_cart") or 0) for p in products.values())
    store_purch = sum(int(p.get("purchases") or 0) for p in products.values())
    baseline = (store_purch / store_adds) if store_adds > 0 else 0.0
    candidates: list[tuple[float, str, dict[str, Any]]] = []
    for pid, p in products.items():
        adds = int(p.get("add_to_cart") or 0)
        purch = int(p.get("purchases") or 0)
        if adds < MIN_PRODUCT_ATC:
            continue
        rate = purch / adds
        if rate <= MAX_CONVERSION_WEAK and (baseline <= 0 or rate < baseline * 0.6):
            gap = (baseline - rate) if baseline > rate else (MAX_CONVERSION_WEAK - rate)
            candidates.append((gap * adds, pid, p))
    if not candidates:
        return []
    candidates.sort(key=lambda x: -x[0])
    _gap, pid, p = candidates[0]
    name = str(p.get("name_ar") or pid)
    adds = int(p.get("add_to_cart") or 0)
    purch = int(p.get("purchases") or 0)
    rate = purch / max(adds, 1)
    conf_l, conf_s = _conf(adds)
    f = _base(
        ev, TYPE_HIGH_INTEREST_LOW_PURCHASE, f"finding:{TYPE_HIGH_INTEREST_LOW_PURCHASE}:{pid}"
    )
    f.update(
        {
            "finding_scope": SCOPE_PRODUCT,
            "scope_reference": pid,
            "title": f"{name} يجذب اهتماماً مرتفعاً لكن نادراً ما يصل إلى الشراء",
            "merchant_summary": (
                f"أُضيف {name} إلى السلة {adds} مرة عبر {int(p.get('unique_carts') or 0)} سلة، "
                f"بينما اكتمل الشراء {purch} مرة فقط ({rate:.0%})."
            ),
            "commercial_meaning": (
                "الاهتمام موجود، لكن مسار الشراء يتعثّر قبل الإتمام — الفرصة التجارية معلّقة."
            ),
            "evidence_summary": (
                f"add_to_cart={adds} unique_carts={p.get('unique_carts')} "
                f"purchases={purch} store_baseline={baseline:.0%}"
            ),
            "sample_size": adds,
            "confidence_level": conf_l,
            "confidence_score": conf_s,
            "business_impact": "تحويل جزء صغير من هذا الاهتمام إلى شراء يرفع الإيراد دون زيادة زيارات.",
            "recommended_direction": (
                "اختبر مراجعة السعر أو وضوح العرض أو تفاصيل المنتج — دون الجزم بسبب واحد."
            ),
            "recommendation_type": REC_TEST,
            "status": STATUS_CONFIRMED if adds >= 15 else STATUS_EMERGING,
            "authoritative_surface": SURFACE_PRODUCTS,
            "home_eligible": True,
            "family_key": "product_conversion",
            "is_hypothesis": False,
            "is_confirmed_cause": False,
        }
    )
    return [f]


def evaluate_low_product_interest_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    products = dict(ev.products or {})
    if len(products) < 3:
        return []
    scored = [
        (int(p.get("add_to_cart") or 0), pid, p) for pid, p in products.items()
    ]
    scored.sort(key=lambda x: -x[0])
    peers = [s for s in scored if s[0] >= MIN_PEER_ATC]
    if len(peers) < 2:
        return []
    peer_median = peers[len(peers) // 2][0]
    weak = [s for s in scored if 0 < s[0] < peer_median * LOW_INTEREST_RATIO]
    if not weak:
        # also catch near-zero vs active peers
        weak = [s for s in scored if s[0] > 0 and s[0] <= 2 and peer_median >= MIN_PEER_ATC]
    if not weak:
        return []
    adds, pid, p = weak[0]
    name = str(p.get("name_ar") or pid)
    f = _base(ev, TYPE_LOW_PRODUCT_INTEREST, f"finding:{TYPE_LOW_PRODUCT_INTEREST}:{pid}")
    f.update(
        {
            "finding_scope": SCOPE_PRODUCT,
            "scope_reference": pid,
            "title": f"{name} يحصل على اهتمام أضعف بكثير من منتجات مشابهة",
            "merchant_summary": (
                f"أُضيف {name} {adds} مرة فقط، بينما منتجات مقارنة تتجاوز حوالي {peer_median} إضافة."
            ),
            "commercial_meaning": (
                "ضعف الاهتمام يقلّل فرص التحويل حتى قبل مرحلة التردد أو الاسترجاع."
            ),
            "evidence_summary": f"product_atc={adds} peer_median_atc={peer_median}",
            "sample_size": adds + peer_median,
            "confidence_level": CONFIDENCE_MEDIUM if peer_median >= 12 else CONFIDENCE_LOW,
            "confidence_score": 0.55 if peer_median >= 12 else 0.35,
            "business_impact": "تحسين ظهور هذا المنتج قد يوسّع قاعدة السلال المحتملة.",
            "recommended_direction": (
                "اختبر الصور أو طريقة العرض أو السعر أو مصدر الزيارة — كتوصيات اختبار لا كأسباب مؤكدة."
            ),
            "recommendation_type": REC_TEST,
            "status": STATUS_EMERGING,
            "authoritative_surface": SURFACE_PRODUCTS,
            "home_eligible": True,
            "family_key": "product_interest",
            "is_confirmed_cause": False,
        }
    )
    return [f]


def evaluate_return_without_purchase_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    total = int(ev.returns_total or 0)
    without = int(ev.returns_without_purchase or 0)
    with_p = int(ev.returns_with_purchase or 0)
    if total < MIN_RETURN_SAMPLE:
        f = _base(
            ev,
            TYPE_RETURN_WITHOUT_PURCHASE,
            f"finding:{TYPE_RETURN_WITHOUT_PURCHASE}:insufficient",
        )
        f.update(
            {
                "title": "عودة العملاء بعد التواصل ما زالت بعينة صغيرة",
                "merchant_summary": (
                    f"عدد حالات العودة المسجّلة ({total}) لا يكفي بعد لاستنتاج موثوق."
                ),
                "commercial_meaning": "لا يمكن الجزم بفعالية الاسترجاع في إغلاق الشراء بعد.",
                "evidence_summary": f"returns={total}",
                "sample_size": total,
                "status": STATUS_INSUFFICIENT,
                "recommendation_type": REC_INSUFFICIENT,
                "recommended_direction": "واصل متابعة العودة والشراء لأيام إضافية.",
                "authoritative_surface": SURFACE_CUSTOMERS,
                "home_eligible": False,
                "family_key": "return_outcome",
            }
        )
        return [f]
    share = without / max(total, 1)
    if share < 0.55:
        return []
    conf_l, conf_s = _conf(total)
    f = _base(ev, TYPE_RETURN_WITHOUT_PURCHASE, f"finding:{TYPE_RETURN_WITHOUT_PURCHASE}")
    f.update(
        {
            "finding_scope": SCOPE_STORE,
            "title": "العملاء يعودون بعد التواصل لكن أغلبهم لا يُكمل الشراء",
            "merchant_summary": (
                f"من أصل {total} عودة مسجّلة، غادر {without} دون شراء ({share:.0%}) "
                f"واكتمل الشراء في {with_p} فقط."
            ),
            "commercial_meaning": (
                "الاسترجاع يُعيد الاهتمام، لكن عائق الشراء ما زال قائماً بعد العودة."
            ),
            "evidence_summary": (
                f"returns={total} without_purchase={without} with_purchase={with_p} "
                f"wa_sent={ev.wa_sent}"
            ),
            "sample_size": total,
            "confidence_level": conf_l,
            "confidence_score": conf_s,
            "business_impact": "تحسين ما يحدث بعد العودة أهم من زيادة عدد الرسائل فقط.",
            "recommended_direction": (
                "افحص سبب التردد بعد العودة، واختبر تحسين العرض أو المتابعة — دون ادعاء سبب نهائي."
            ),
            "recommendation_type": REC_INVESTIGATE,
            "status": STATUS_CONFIRMED,
            "authoritative_surface": SURFACE_CUSTOMERS,
            "home_eligible": True,
            "family_key": "return_outcome",
        }
    )
    return [f]


def evaluate_recovery_channel_effectiveness_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    sent = int(ev.wa_sent or 0)
    returned = int(ev.wa_returned or 0)
    purchased = int(ev.wa_purchased or 0)
    failed = int(ev.wa_failed or 0)
    if sent >= MIN_WA_SENT:
        ret_rate = returned / max(sent, 1)
        purch_rate = purchased / max(sent, 1)
        conf_l, conf_s = _conf(sent)
        f = _base(
            ev,
            TYPE_RECOVERY_CHANNEL_EFFECTIVENESS,
            f"finding:{TYPE_RECOVERY_CHANNEL_EFFECTIVENESS}:whatsapp",
        )
        if purch_rate >= 0.25 and returned >= MIN_WA_RETURN:
            title = "مسار واتساب يُنتج مشتريات بدليل كافٍ حالياً"
            meaning = "الرسائل لا تقتصر على لفت الانتباه — بل ترتبط بإتمام شراء في جزء ملموس من الحالات."
            rec = REC_MONITOR
            status = STATUS_CONFIRMED
            summary = (
                f"من {sent} رسالة، عاد {returned} واشترى {purchased} "
                f"(شراء ≈ {purch_rate:.0%} من الرسائل)."
            )
        elif ret_rate >= 0.35 and purch_rate <= MAX_WA_PURCHASE_RATE:
            title = "واتساب يُعيد العملاء، لكن إتمام الشراء ما زال ضعيفاً"
            meaning = "القناة تُحرّك العودة، بينما قيمة الإيراد تتحقق عند إغلاق الشراء بعد العودة."
            rec = REC_INVESTIGATE
            status = STATUS_CONFIRMED
            summary = (
                f"عادات العودة واضحة ({returned}/{sent}) بينما الشراء ({purchased}) "
                f"ما زال منخفضاً نسبياً."
            )
        else:
            title = "فعالية واتساب التجارية ما زالت قيد التشكّل"
            meaning = "الإشارات مختلطة أو العينة لا تدعم حكماً قوياً بعد."
            rec = REC_MONITOR
            status = STATUS_EMERGING
            summary = (
                f"أُرسل {sent} · عاد {returned} · اشترى {purchased} · فشل {failed}."
            )
        f.update(
            {
                "finding_scope": SCOPE_RECOVERY_CHANNEL,
                "scope_reference": "whatsapp",
                "title": title,
                "merchant_summary": summary,
                "commercial_meaning": meaning,
                "evidence_summary": (
                    f"sent={sent} returned={returned} purchased={purchased} "
                    f"failed={failed} suppressed={ev.wa_suppressed}"
                ),
                "sample_size": sent,
                "confidence_level": conf_l,
                "confidence_score": conf_s,
                "business_impact": "قياس العودة والشراء معاً يمنع المبالغة في نجاح القناة.",
                "recommended_direction": (
                    "حافظ على القناة إن كانت تُعيد الاهتمام، وركّز التحسين على ما بعد العودة."
                    if purch_rate < 0.25
                    else "واصل القياس؛ لا تغيّر القناة دون سبب أوضح."
                ),
                "recommendation_type": rec,
                "status": status,
                "authoritative_surface": SURFACE_WHATSAPP,
                "home_eligible": True,
                "family_key": "channel_whatsapp",
            }
        )
        out.append(f)

    reasons = int(ev.widget_reasons_captured or 0)
    contacts = int(ev.widget_contact_captured or 0)
    if reasons >= 8:
        contact_rate = contacts / max(reasons, 1)
        f2 = _base(
            ev,
            TYPE_RECOVERY_CHANNEL_EFFECTIVENESS,
            f"finding:{TYPE_RECOVERY_CHANNEL_EFFECTIVENESS}:widget",
        )
        if contact_rate < 0.35:
            f2.update(
                {
                    "finding_scope": SCOPE_RECOVERY_CHANNEL,
                    "scope_reference": "widget",
                    "title": "التفاعل يلتقط أسباب التردد لكن بيانات التواصل ما زالت ضعيفة",
                    "merchant_summary": (
                        f"سُجّل {reasons} سبب تردد، بينما اكتملت وسيلة التواصل في {contacts} فقط "
                        f"({contact_rate:.0%})."
                    ),
                    "commercial_meaning": (
                        "معرفة سبب التردد دون تواصل صالح تُبقي كثيراً من السلال خارج الاسترجاع."
                    ),
                    "evidence_summary": f"reasons={reasons} contacts={contacts}",
                    "sample_size": reasons,
                    "confidence_level": CONFIDENCE_MEDIUM,
                    "confidence_score": 0.6,
                    "business_impact": "كل سبب بلا تواصل يقلّل فرصة المتابعة التجارية.",
                    "recommended_direction": (
                        "اختبر تحسين لحظة طلب التواصل بعد التقاط السبب — كتوصية اختبار."
                    ),
                    "recommendation_type": REC_TEST,
                    "status": STATUS_CONFIRMED,
                    "authoritative_surface": SURFACE_CARTS,
                    "home_eligible": True,
                    "family_key": "channel_widget",
                }
            )
            out.append(f2)
    return out


def evaluate_whatsapp_test_candidate_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    sent = int(ev.wa_sent or 0)
    returned = int(ev.wa_returned or 0)
    purchased = int(ev.wa_purchased or 0)
    failed = int(ev.wa_failed or 0)
    if sent < MIN_WA_SENT or returned < MIN_WA_RETURN:
        return []
    if failed / max(sent, 1) >= 0.35:
        return []  # channel failure is primary — not wording/timing
    purch_rate = purchased / max(sent, 1)
    ret_rate = returned / max(sent, 1)
    if not (ret_rate >= 0.40 and purch_rate <= MAX_WA_PURCHASE_RATE):
        return []
    f = _base(ev, TYPE_WHATSAPP_TEST_CANDIDATE, f"finding:{TYPE_WHATSAPP_TEST_CANDIDATE}")
    f.update(
        {
            "finding_scope": SCOPE_RECOVERY_CHANNEL,
            "scope_reference": "whatsapp",
            "title": "العودة بعد واتساب متكررة والشراء ضعيف — يستحق اختبار الرسالة أو التوقيت",
            "merchant_summary": (
                f"بعد {sent} رسالة عاد {returned} عميل تقريباً، لكن الشراء اكتمل {purchased} مرة فقط."
            ),
            "commercial_meaning": (
                "الدليل يبرر اختبار صياغة أو وقت إرسال مختلف — دون الجزم بأن الصياغة الحالية هي السبب."
            ),
            "evidence_summary": (
                f"sent={sent} returned={returned} purchased={purchased} "
                f"failed={failed} failed_share={failed/max(sent,1):.0%}"
            ),
            "sample_size": sent,
            "confidence_level": CONFIDENCE_MEDIUM,
            "confidence_score": 0.62,
            "business_impact": "اختبار محكوم قد يرفع إغلاق الشراء لنفس حجم الرسائل.",
            "recommended_direction": "اختبر رسالة أو وقت إرسال واحد، وقارن العودة والشراء.",
            "recommendation_type": REC_TEST,
            "status": STATUS_EMERGING,
            "authoritative_surface": SURFACE_WHATSAPP,
            "home_eligible": True,
            "family_key": "channel_whatsapp_test",
            "is_confirmed_cause": False,
            "is_hypothesis": False,
        }
    )
    return [f]


def evaluate_traffic_versus_conversion_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    f = _base(ev, TYPE_TRAFFIC_VS_CONVERSION, f"finding:{TYPE_TRAFFIC_VS_CONVERSION}")
    if not ev.has_visitor_truth or ev.visitor_total is None:
        f.update(
            {
                "title": "لا يمكن بعد التمييز بين ضعف الزيارات وضعف التحويل",
                "merchant_summary": (
                    "بيانات زيارات المتجر الموثوقة غير متاحة حالياً، "
                    "ولا يصح استنتاج حجم الزيارات من عدد السلال وحدها."
                ),
                "commercial_meaning": (
                    "أي توصية إعلانية أو مرورية الآن ستكون افتراضاً لا دليلاً."
                ),
                "evidence_summary": "visitor_total=unavailable; carts_not_used_as_traffic_proxy",
                "sample_size": int(ev.active_carts or 0),
                "status": STATUS_INSUFFICIENT,
                "recommendation_type": REC_INSUFFICIENT,
                "recommended_direction": (
                    "اربط مصدر زيارات موثوقاً قبل الحكم على الزيارات مقابل التحويل."
                ),
                "confidence_level": CONFIDENCE_INSUFFICIENT,
                "confidence_score": 0.0,
                "authoritative_surface": SURFACE_KNOWLEDGE,
                "home_eligible": True,
                "family_key": "traffic_conversion",
            }
        )
        return [f]
    # Future path when visitor truth exists
    visitors = int(ev.visitor_total or 0)
    carts = int(ev.active_carts or 0)
    purch = int(ev.purchased_carts or 0)
    if visitors <= 0:
        f["status"] = STATUS_INSUFFICIENT
        f["title"] = "حجم الزيارات غير كافٍ للحكم"
        f["merchant_summary"] = "لا زيارات موثوقة في النافذة الحالية."
        f["recommendation_type"] = REC_INSUFFICIENT
        return [f]
    cart_rate = carts / visitors
    purch_rate = purch / max(carts, 1)
    if cart_rate >= 0.05 and purch_rate < 0.15:
        title = "النشاط يصل إلى السلة، لكن القليل منه يتحول إلى شراء"
        rec = REC_INVESTIGATE
    elif cart_rate < 0.02 and purch_rate >= 0.2:
        title = "التحويل مقبول نسبياً، لكن حجم الزيارات منخفض لبناء مبيعات ثابتة"
        rec = REC_INVESTIGATE
    else:
        title = "الصورة مختلطة بين الزيارات والتحويل"
        rec = REC_MONITOR
    f.update(
        {
            "title": title,
            "merchant_summary": (
                f"زيارات={visitors} · سلال={carts} · مشتريات={purch}."
            ),
            "commercial_meaning": "تشخيص الزيارات مقابل التحويل يوجّه إن كان الاستثمار في جلب زوار أو إغلاق شراء.",
            "evidence_summary": f"visitors={visitors} carts={carts} purchases={purch}",
            "sample_size": visitors,
            "recommendation_type": rec,
            "status": STATUS_EMERGING,
            "authoritative_surface": SURFACE_KNOWLEDGE,
            "home_eligible": True,
            "family_key": "traffic_conversion",
            "confidence_level": CONFIDENCE_MEDIUM,
            "confidence_score": 0.55,
        }
    )
    return [f]


def evaluate_repeated_interest_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    products = dict(ev.products or {})
    best = None
    best_score = 0
    for pid, p in products.items():
        repeat = int(p.get("repeat_adds") or 0)
        revisits = int(p.get("revisits") or 0)
        purch = int(p.get("purchases") or 0)
        adds = int(p.get("add_to_cart") or 0)
        if adds < MIN_REPEAT_ATC:
            continue
        if purch > 0 and purch / max(adds, 1) > 0.2:
            continue
        score = repeat * 2 + revisits * 3
        if score > best_score:
            best_score = score
            best = (pid, p, repeat, revisits)
    if not best or best_score < 6:
        if int(ev.repeated_returners or 0) >= 4 and int(ev.returns_without_purchase or 0) >= 6:
            f = _base(ev, TYPE_REPEATED_INTEREST, f"finding:{TYPE_REPEATED_INTEREST}:customers")
            f.update(
                {
                    "finding_scope": SCOPE_STORE,
                    "title": "هناك عملاء يعودون مراراً دون إتمام الشراء",
                    "merchant_summary": (
                        f"{ev.repeated_returners} نمط عودة متكرر مع استمرار غياب الشراء في أغلب الحالات."
                    ),
                    "commercial_meaning": "اهتمام غير محسوم يتراكم — فرصة إن عُالج عائق الشراء.",
                    "evidence_summary": (
                        f"repeated_returners={ev.repeated_returners} "
                        f"returns_without_purchase={ev.returns_without_purchase}"
                    ),
                    "sample_size": int(ev.repeated_returners),
                    "confidence_level": CONFIDENCE_MEDIUM,
                    "confidence_score": 0.58,
                    "recommended_direction": "راجع أسباب التردد لدى العائدين و sensitize المتابعة.",
                    "recommendation_type": REC_INVESTIGATE,
                    "status": STATUS_EMERGING,
                    "authoritative_surface": SURFACE_CUSTOMERS,
                    "home_eligible": True,
                    "family_key": "repeated_interest",
                }
            )
            # Fix accidental English in Arabic copy
            f["recommended_direction"] = (
                "راجع أسباب التردد لدى العائدين وركّز المتابعة على إغلاق الشراء."
            )
            return [f]
        return []
    pid, p, repeat, revisits = best
    name = str(p.get("name_ar") or pid)
    f = _base(ev, TYPE_REPEATED_INTEREST, f"finding:{TYPE_REPEATED_INTEREST}:{pid}")
    f.update(
        {
            "finding_scope": SCOPE_PRODUCT,
            "scope_reference": pid,
            "title": f"{name} ي吸引 اهتماماً متكرراً عبر زيارات متعددة دون شراء",
            "merchant_summary": (
                f"ظاهرة إعادة إضافة/{repeat} وإشارات عودة/{revisits} حول {name} "
                f"مع مشتريات={int(p.get('purchases') or 0)} فقط."
            ),
            "commercial_meaning": "اهتمام متكرر غير محسوم غالباً يعني فرصة ضائعة أكثر من ضعف اهتمام.",
            "evidence_summary": (
                f"repeat_adds={repeat} revisits={revisits} "
                f"add_to_cart={p.get('add_to_cart')} purchases={p.get('purchases')}"
            ),
            "sample_size": int(p.get("add_to_cart") or 0),
            "confidence_level": CONFIDENCE_MEDIUM,
            "confidence_score": 0.6,
            "business_impact": "إغلاق جزء من الاهتمام المتكرر يرفع الإيراد من نفس الزوار.",
            "recommended_direction": "اختبر عرضاً أو تذكيراً موجّهاً لهذا المنتج بعد العودة.",
            "recommendation_type": REC_TEST,
            "status": STATUS_EMERGING,
            "authoritative_surface": SURFACE_PRODUCTS,
            "home_eligible": True,
            "family_key": "repeated_interest",
        }
    )
    # Fix mixed language title - use proper Arabic
    f["title"] = f"{name} يجذب اهتماماً متكرراً عبر زيارات متعددة دون شراء"
    f["merchant_summary"] = (
        f"ظَهرت إعادة إضافة ({repeat}) وإشارات عودة ({revisits}) حول {name}، "
        f"بينما المشتريات = {int(p.get('purchases') or 0)} فقط."
    )
    return [f]


def evaluate_hesitation_resolution_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    resolved = dict(ev.hesitation_resolved or {})
    if not resolved:
        return []
    out: list[dict[str, Any]] = []
    best_ok = None
    best_bad = None
    for reason, stats in resolved.items():
        ret = int(stats.get("returned") or 0)
        purch = int(stats.get("purchased") or 0)
        unresolved = int(stats.get("unresolved") or 0)
        if ret + purch + unresolved < 4:
            continue
        rate = purch / max(ret, 1) if ret else 0.0
        row = (rate, reason, ret, purch, unresolved)
        if purch >= 2 and rate >= 0.5:
            if best_ok is None or rate > best_ok[0]:
                best_ok = row
        if unresolved >= 4 and rate <= 0.25:
            if best_bad is None or unresolved > best_bad[4]:
                best_bad = row
    if best_ok:
        _rate, reason, ret, purch, unresolved = best_ok
        label = reason_label_ar(reason)
        f = _base(
            ev,
            TYPE_HESITATION_RESOLUTION,
            f"finding:{TYPE_HESITATION_RESOLUTION}:resolved:{reason}",
        )
        f.update(
            {
                "finding_scope": SCOPE_HESITATION_REASON,
                "scope_reference": reason,
                "title": f"من يذكرون «{label}» كثيراً ما يعودون ويُكملون الشراء",
                "merchant_summary": (
                    f"بعد العودة ({ret}) اكتمل الشراء {purch} مرة لهذا السبب — نسبة حل أعلى من غيره."
                ),
                "commercial_meaning": "هذا السبب قابل للحل نسبياً بعد التواصل أو العودة.",
                "evidence_summary": f"reason={reason} returned={ret} purchased={purch}",
                "sample_size": ret,
                "confidence_level": CONFIDENCE_MEDIUM,
                "confidence_score": 0.58,
                "recommended_direction": "حافظ على مسار المتابعة لهذا السبب ووثّق ما ينجح.",
                "recommendation_type": REC_MONITOR,
                "status": STATUS_CONFIRMED,
                "authoritative_surface": SURFACE_KNOWLEDGE,
                "home_eligible": True,
                "family_key": "hesitation_resolution",
            }
        )
        out.append(f)
    if best_bad:
        _rate, reason, ret, purch, unresolved = best_bad
        label = reason_label_ar(reason)
        f = _base(
            ev,
            TYPE_HESITATION_RESOLUTION,
            f"finding:{TYPE_HESITATION_RESOLUTION}:unresolved:{reason}",
        )
        f.update(
            {
                "finding_scope": SCOPE_HESITATION_REASON,
                "scope_reference": reason,
                "title": f"تردّد «{label}» يبقى غالباً بلا حل حتى بعد التواصل",
                "merchant_summary": (
                    f"حالات غير محلولة ≈ {unresolved} مع مشتريات={purch} بعد العودة={ret}."
                ),
                "commercial_meaning": (
                    "التواصل وحده لا يُزيل هذا العائق — يلزم اختبار عرض أو سياسة مرتبطة به."
                ),
                "evidence_summary": (
                    f"reason={reason} unresolved={unresolved} returned={ret} purchased={purch}"
                ),
                "sample_size": unresolved + ret,
                "confidence_level": CONFIDENCE_MEDIUM,
                "confidence_score": 0.6,
                "recommended_direction": (
                    "اختبر تحسيناً واحداً مرتبطاً بهذا السبب وقِس الشراء بعد العودة."
                ),
                "recommendation_type": REC_TEST,
                "status": STATUS_CONFIRMED,
                "authoritative_surface": SURFACE_KNOWLEDGE,
                "home_eligible": True,
                "family_key": "hesitation_resolution",
            }
        )
        out.append(f)
    return out


def evaluate_insufficient_or_conflicting_v1(
    ev: EvidenceBundle, produced: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    produced_list = [p for p in produced if isinstance(p, dict)]
    confirmed = [
        p
        for p in produced_list
        if p.get("status") in (STATUS_CONFIRMED, STATUS_EMERGING)
        and p.get("recommendation_type") not in (REC_INSUFFICIENT,)
        and p.get("finding_type") != TYPE_INSUFFICIENT_OR_CONFLICTING
    ]
    # Conflicting: strong WA purchase success + strong return-without-purchase both confirmed
    types = {p.get("finding_type") for p in confirmed}
    titles = " ".join(str(p.get("title") or "") for p in confirmed)
    conflict = False
    if (
        TYPE_RETURN_WITHOUT_PURCHASE in types
        and any("يُنتج مشتريات" in str(p.get("title") or "") for p in confirmed)
    ):
        conflict = True
    # Equal dual hesitation dominance already handled; conflicting products interest
    dist = dict(ev.hesitation_distribution or {})
    if len(dist) >= 2:
        vals = sorted(dist.values(), reverse=True)
        if vals[0] == vals[1] and vals[0] >= 8:
            conflict = True

    out: list[dict[str, Any]] = []
    if conflict:
        f = _base(
            ev,
            TYPE_INSUFFICIENT_OR_CONFLICTING,
            f"finding:{TYPE_INSUFFICIENT_OR_CONFLICTING}:conflict",
        )
        f.update(
            {
                "title": "سلوك العملاء يشير حالياً إلى اتجاهات متعارضة",
                "merchant_summary": (
                    "بعض الإشارات تدعم نجاح مسار، وأخرى تُظهر ضعفاً في الإغلاق — "
                    "لا نُصدر توصية أحادية قوية الآن."
                ),
                "commercial_meaning": (
                    "التعارض يعني أن القرار المتسرّع قد يُصلح جانباً ويُفسد آخر."
                ),
                "evidence_summary": f"confirmed_types={sorted(types)}; titles_blob_len={len(titles)}",
                "sample_size": int(ev.hesitation_total or 0) + int(ev.wa_sent or 0),
                "status": STATUS_CONFLICTING,
                "recommendation_type": REC_INVESTIGATE,
                "recommended_direction": "افصل الشرائح (سبب/منتج/قناة) قبل تغيير واسع.",
                "confidence_level": CONFIDENCE_MEDIUM,
                "confidence_score": 0.5,
                "authoritative_surface": SURFACE_KNOWLEDGE,
                "home_eligible": True,
                "family_key": "meta_evidence",
            }
        )
        out.append(f)

    actionable = [
        p
        for p in confirmed
        if p.get("recommendation_type") in (REC_ACT_NOW, REC_TEST, REC_INVESTIGATE)
        and p.get("status") != STATUS_INSUFFICIENT
    ]
    if len(actionable) == 0 and not conflict:
        f = _base(
            ev,
            TYPE_INSUFFICIENT_OR_CONFLICTING,
            f"finding:{TYPE_INSUFFICIENT_OR_CONFLICTING}:insufficient",
        )
        f.update(
            {
                "title": "لا يوجد بعد دليل كافٍ للتوصية بتغيير",
                "merchant_summary": (
                    "البيانات الحالية لا تدعم استنتاجاً تجارياً آمناً بما يكفي لتوجيه قرار."
                ),
                "commercial_meaning": "الامتناع عن التوصية أفضل من نصيحة ضعيفة الدليل.",
                "evidence_summary": (
                    f"hesitation={ev.hesitation_total} wa_sent={ev.wa_sent} "
                    f"products={len(ev.products or {})}"
                ),
                "sample_size": int(ev.hesitation_total or 0) + int(ev.wa_sent or 0),
                "status": STATUS_INSUFFICIENT,
                "recommendation_type": REC_INSUFFICIENT,
                "recommended_direction": "واصل التشغيل واجمع أدلة التردد والعودة والشراء.",
                "confidence_level": CONFIDENCE_INSUFFICIENT,
                "confidence_score": 0.1,
                "authoritative_surface": SURFACE_KNOWLEDGE,
                "home_eligible": True,
                "family_key": "meta_evidence",
            }
        )
        out.append(f)
    return out


def evaluate_all_families_v1(ev: EvidenceBundle) -> list[dict[str, Any]]:
    """Run all V1 families; meta findings see prior outputs."""
    findings: list[dict[str, Any]] = []
    findings.extend(evaluate_missing_contact_v1(ev))
    findings.extend(evaluate_dominant_hesitation_v1(ev))
    findings.extend(evaluate_high_interest_low_purchase_v1(ev))
    findings.extend(evaluate_low_product_interest_v1(ev))
    findings.extend(evaluate_return_without_purchase_v1(ev))
    findings.extend(evaluate_recovery_channel_effectiveness_v1(ev))
    findings.extend(evaluate_whatsapp_test_candidate_v1(ev))
    findings.extend(evaluate_traffic_versus_conversion_v1(ev))
    findings.extend(evaluate_repeated_interest_v1(ev))
    findings.extend(evaluate_hesitation_resolution_v1(ev))
    findings.extend(evaluate_insufficient_or_conflicting_v1(ev, findings))
    return findings
