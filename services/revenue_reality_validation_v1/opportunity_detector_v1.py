# -*- coding: utf-8 -*-
"""Bounded opportunity detector over isolated simulation truth."""
from __future__ import annotations

from typing import Any

from services.revenue_reality_validation_v1.contracts_v1 import (
    MISSION_STATUS_ACTIVE,
    MISSION_STATUS_INSUFFICIENT,
    MISSION_STATUS_MEASURING,
    MISSION_STATUS_PROPOSED,
    MISSION_STATUS_WON,
    SIMULATION_STORE_SLUG,
    empty_opportunity_v1,
    validate_opportunity_v1,
)

# Evidence thresholds (falsifiable)
MIN_VIEWS_DISCOVERY_COMPARE = 80
MIN_ATC_FOR_CONVERSION_DIAG = 40
MIN_HESITATION_SHARE = 0.35
MIN_HESITATION_COUNT = 25
MIN_CHANNEL_VIEWS = 120
MIN_CHANNEL_ATC = 25
MIN_CO_OCCURRENCE = 15
MIN_RETENTION_BUYERS = 20
MIN_AMBIGUOUS_VIEWS_FOR_ACTION = 100


def _opp(
    *,
    opportunity_id: str,
    scenario_id: str,
    scope: dict[str, Any],
    evidence: list[str],
    diagnosis: str,
    commercial_opportunity: str,
    recommended_action: str,
    why: str,
    measurement_plan: str,
    recheck_condition: str,
    confidence: str,
    status: str,
    falsifiers: list[str],
) -> dict[str, Any]:
    o = empty_opportunity_v1()
    o.update(
        {
            "ok": True,
            "opportunity_id": opportunity_id,
            "store_slug": SIMULATION_STORE_SLUG,
            "scope": scope,
            "evidence": evidence,
            "diagnosis": diagnosis,
            "commercial_opportunity": commercial_opportunity,
            "recommended_action": recommended_action,
            "why": why,
            "measurement_plan": measurement_plan,
            "recheck_condition": recheck_condition,
            "confidence": confidence,
            "status": status,
            "scenario_id": scenario_id,
            "falsifiers": falsifiers,
            "simulation_only": True,
        }
    )
    errs = validate_opportunity_v1(o)
    o["ok"] = not errs
    o["validation_errors"] = errs
    return o


def detect_opportunities_v1(world: dict[str, Any]) -> list[dict[str, Any]]:
    aggs = world.get("aggregates") or {}
    rel = world.get("relationships") or {}
    out: list[dict[str, Any]] = []

    # --- A Discovery ---
    p01 = aggs.get("rrv_p01_discovery") or {}
    peers = [
        a
        for pid, a in aggs.items()
        if pid != "rrv_p01_discovery" and a.get("profile") in ("steady_baseline", "organic_steady")
    ]
    peer_views = sum(int(p["views"]) for p in peers) / max(1, len(peers))
    peer_atc = sum(float(p["atc_rate"]) for p in peers) / max(1, len(peers))
    if (
        int(p01.get("views") or 0) < peer_views * 0.45
        and float(p01.get("atc_rate") or 0) >= peer_atc * 1.4
        and float(p01.get("purchase_rate_of_atc") or 0) >= 0.30
        and int(p01.get("views") or 0) >= 30
    ):
        out.append(
            _opp(
                opportunity_id="opp_a_discovery_p01",
                scenario_id="A_discovery",
                scope={"type": "product", "id": "rrv_p01_discovery", "name_ar": p01.get("name_ar")},
                evidence=[
                    f"مشاهدات منخفضة خلال {world.get('days')} يومًا: {p01.get('views')} مقابل متوسط أقران ~{int(peer_views)}",
                    f"معدل إضافة للسلة قوي عند الاكتشاف: {p01.get('atc_rate'):.1%} (أقران ~{peer_atc:.1%})",
                    f"شراء مقبول بعد الإضافة: {p01.get('purchase_rate_of_atc'):.1%} من ATC",
                    f"إيراد محقق رغم الندرة: {p01.get('revenue')} ر.س",
                ],
                diagnosis=(
                    "الفرصة الأرجح اكتشاف/توزيع: المنتج يُحوَّل جيدًا عند رؤيته، "
                    "وليس دليلًا كافيًا على مشكلة سعر فورية."
                ),
                commercial_opportunity="زيادة الاكتشاف المؤهل للمنتج دون افتراض قناة إعلانية محددة.",
                recommended_action=(
                    "اختبار وضع أقوى في الصفحة الرئيسية/التصنيف، و/أو تجربة محتوى/توزيع محدودة المدة، "
                    "مع قياس الاكتشاف والتحويل معًا."
                ),
                why=(
                    "انخفاض المشاهدات مع ATC وتحويل شراء مقبول يشير إلى نقص وصول مؤهل، "
                    "لا إلى فشل عرض المنتج بعد الاكتشاف."
                ),
                measurement_plan=(
                    "مراقبة: مشاهدات المنتج، ATC rate، شراء من ATC، إيراد المنتج — "
                    "مقارنة بأساس الـ30 يومًا قبل التجربة."
                ),
                recheck_condition=(
                    "إعادة التقييم بعد 14 يومًا من بدء التجربة، أو عند +40% مشاهدات مع ثبات/تحسن ATC."
                ),
                confidence="medium",
                status=MISSION_STATUS_PROPOSED,
                falsifiers=[
                    "إذا بقيت المشاهدات منخفضة وATC منخفضًا معًا → ليست فرصة اكتشاف.",
                    "إذا ارتفعت المشاهدات وانخفض ATC بحدة → قد تكون جودة الزيارات ضعيفة وليس مجرد توزيع.",
                    "لا توصية بقناة إعلان محددة دون دليل قناة لهذا المنتج.",
                ],
            )
        )
    else:
        out.append(
            _opp(
                opportunity_id="opp_a_discovery_p01_fail",
                scenario_id="A_discovery",
                scope={"type": "product", "id": "rrv_p01_discovery"},
                evidence=["شروط الاكتشاف غير متحققة في المحاكاة."],
                diagnosis="لا يكفي لاعتبارها فرصة اكتشاف.",
                commercial_opportunity="لا إجراء تجاري مقترح.",
                recommended_action="جمع مزيد من مشاهدات/ATC قبل الحكم.",
                why="العتبات غير مستوفاة.",
                measurement_plan="انتظار عتبة مشاهدات كافية.",
                recheck_condition=f"عند تجاوز {MIN_VIEWS_DISCOVERY_COMPARE} مشاهدة مع ATC قابل للمقارنة.",
                confidence="insufficient",
                status=MISSION_STATUS_INSUFFICIENT,
                falsifiers=["أي توصية اكتشاف بدون فرق مشاهدات+ATC قوي."],
            )
        )

    # --- B High interest / low conversion (shipping) ---
    p02 = aggs.get("rrv_p02_friction") or {}
    hes = p02.get("hesitation") or {}
    abandons = max(1, int(p02.get("abandons") or 0))
    ship_share = float(hes.get("shipping") or 0) / abandons
    if (
        int(p02.get("atc") or 0) >= MIN_ATC_FOR_CONVERSION_DIAG
        and float(p02.get("atc_rate") or 0) >= 0.15
        and float(p02.get("purchase_rate_of_atc") or 0) < 0.20
        and ship_share >= MIN_HESITATION_SHARE
        and int(hes.get("shipping") or 0) >= MIN_HESITATION_COUNT
    ):
        out.append(
            _opp(
                opportunity_id="opp_b_shipping_friction_p02",
                scenario_id="B_high_interest_low_conversion",
                scope={"type": "product", "id": "rrv_p02_friction", "name_ar": p02.get("name_ar")},
                evidence=[
                    f"اهتمام مرتفع: مشاهدات {p02.get('views')}، ATC {p02.get('atc')} ({p02.get('atc_rate'):.1%})",
                    f"إكمال شراء ضعيف من ATC: {p02.get('purchase_rate_of_atc'):.1%}",
                    f"هيمنة تردد الشحن ضمن الترددات: {hes.get('shipping')} من {abandons} هجر ({ship_share:.0%})",
                    f"محاولات استرداد {p02.get('recovery_attempts')} بنجاح {p02.get('recovered_purchases')} — التحويل يبقى ضعيفًا",
                ],
                diagnosis=(
                    "احتكاك ما بعد الاهتمام مرتبط بدليل شحن أقوى من السعر. "
                    "لا يُستنتج خصم فوري من هذه الإشارة."
                ),
                commercial_opportunity="تشخيص وتحسين احتكاك الشحن/التوصيل قبل تجارب السعر.",
                recommended_action=(
                    "مراجعة وضوح تكلفة الشحن وخيارات التوصيل في مسار الشراء، "
                    "واختبار رسالة شحن أوضح — دون خصم منتج كخطوة أولى."
                ),
                why="ATC مرتفع مع شراء ضعيف + هيمنة تردد الشحن يدعم فرضية الاحتكاك اللوجستي.",
                measurement_plan=(
                    "مراقبة: نسبة تردد الشحن، شراء من ATC، استرداد ناجح، إيراد المنتج. "
                    "لا ادّعاء رفع إيراد قبل القياس."
                ),
                recheck_condition="بعد 14 يومًا من تغيير وضوح الشحن، أو إذا انخفضت حصة تردد الشحن تحت 25%.",
                confidence="medium",
                status=MISSION_STATUS_PROPOSED,
                falsifiers=[
                    "إذا كانت حصة تردد الشحن ضعيفة → لا توصية تغيير شحن.",
                    "إذا هيمن تردد السعر → أعد التشخيص نحو السعر لا الشحن.",
                    "لا توصية خصم من ATC مرتفع وحده.",
                ],
            )
        )

    # --- C Price-sensitive (bounded experiment) ---
    p03 = aggs.get("rrv_p03_price") or {}
    hes3 = p03.get("hesitation") or {}
    ab3 = max(1, int(p03.get("abandons") or 0))
    price_share = float(hes3.get("price") or 0) / ab3
    if (
        int(p03.get("atc") or 0) >= MIN_ATC_FOR_CONVERSION_DIAG
        and price_share >= MIN_HESITATION_SHARE
        and int(hes3.get("price") or 0) >= MIN_HESITATION_COUNT
        and float(p03.get("purchase_rate_of_atc") or 0) < 0.20
    ):
        out.append(
            _opp(
                opportunity_id="opp_c_price_experiment_p03",
                scenario_id="C_price_sensitive",
                scope={"type": "product", "id": "rrv_p03_price", "name_ar": p03.get("name_ar")},
                evidence=[
                    f"اهتمام قوي: ATC {p03.get('atc')} من {p03.get('views')} مشاهدة",
                    f"تردّد سعر متكرر: {hes3.get('price')} ({price_share:.0%} من الهجر)",
                    f"تحويل شراء ضعيف: {p03.get('purchase_rate_of_atc'):.1%} من ATC",
                    "عتبة الدليل مستوفاة لتجربة عرض محدودة — بدون uplift متوقع مخترع",
                ],
                diagnosis="حساسية سعر مدعومة بحجم كافٍ لتجربة عرض محدودة بزمن وإيقاف.",
                commercial_opportunity="تجربة عرض/سعر محدودة لقياس أثر الإيراد لا التحويل وحده.",
                recommended_action=(
                    "تشغيل عرض محدود لمدة 10–14 يومًا بحد أقصى خصم محدد مسبقًا، "
                    "مع شرط إيقاف إذا انخفض الإيراد الصافي المقاس أو بقي التحويل دون عتبة."
                ),
                why="دليل تردد السعر + حجم ATC كافٍ؛ التجربة يجب أن تقيس الإيراد لا التحويل فقط.",
                measurement_plan=(
                    "قبل/بعد: شراء من ATC، AOV، إيراد المنتج، حصة تردد السعر. "
                    "ممنوع ادّعاء نجاح دون مقارنة إيراد."
                ),
                recheck_condition=(
                    "إيقاف مبكر إذا انخفض إيراد المنتج >10% خلال 7 أيام؛ "
                    "إعادة تقييم كاملة في يوم 14."
                ),
                confidence="medium",
                status=MISSION_STATUS_PROPOSED,
                falsifiers=[
                    "إذا ضعفت عينة تردد السعر → لا تجربة سعر.",
                    "تحسن التحويل مع إيراد غير حاسم → لا ادّعاء نجاح تجاري.",
                    "لا مقارنة أسعار سوق خارجية في هذه المهمة.",
                ],
            )
        )

    # --- D Discount destroys value ---
    p04 = aggs.get("rrv_p04_discount_trap") or {}
    eco = p04.get("promo_economics_simulation_only") or {}
    if eco.get("conversion_improved") and eco.get("contribution_worse_on_promo"):
        out.append(
            _opp(
                opportunity_id="opp_d_stop_promo_p04",
                scenario_id="D_discount_destroys_value",
                scope={"type": "product", "id": "rrv_p04_discount_trap", "name_ar": p04.get("name_ar")},
                evidence=[
                    f"خلال أيام العرض: مشتريات {eco.get('promo_purchases')}، إيراد {eco.get('promo_revenue')}",
                    f"مساهمة محاكاة (SIMULATION-ONLY): {eco.get('promo_contribution_sim_only')} مقابل غير العرض {eco.get('non_promo_contribution_sim_only')}",
                    "التحويل ارتفع مع العرض لكن الاقتصاد التجاري للمحاكاة أسوأ",
                    str(eco.get("label") or ""),
                ],
                diagnosis=(
                    "رفع التحويل بالخصم لا يكفي؛ الاقتصاد المحاكى يظهر تدمير قيمة المساهمة. "
                    "هامش الإنتاج = فجوة بيانات؛ هذا استنتاج مختبر فقط."
                ),
                commercial_opportunity="إيقاف أو إعادة تصميم العرض بدل الاحتفال برفع التحويل.",
                recommended_action="إيقاف الخصم الحالي أو استبداله بعرض لا يخفض المساهمة تحت عتبة مقبولة.",
                why="قياس الإيراد/المساهمة المحاكاة يُظهر أن التحويل الأعلى كان مضللاً تجاريًا.",
                measurement_plan=(
                    "بعد الإيقاف: تحويل، إيراد، ومساهمة محاكاة إن وُجدت. "
                    "لا احتفال بـ conversion uplift دون اقتصاد."
                ),
                recheck_condition="بعد 14 يومًا من الإيقاف؛ إعادة تقييم إذا عاد ضغط التحويل دون تحسن إيراد.",
                confidence="high",
                status=MISSION_STATUS_PROPOSED,
                falsifiers=[
                    "إذا تحسن الإيراد والمساهمة معًا مع الخصم → ليست مهمة إيقاف.",
                    "بدون تكلفة محاكاة: لا ادّعاء ربح — أبلغ DATA GAP للهامش.",
                ],
            )
        )

    # --- E Bundle ---
    co_list = rel.get("cart_co_occurrence") or []
    for co in co_list:
        if int(co.get("orders_with_both") or 0) >= MIN_CO_OCCURRENCE and str(
            co.get("evidence_strength")
        ) in ("strong", "moderate"):
            out.append(
                _opp(
                    opportunity_id="opp_e_bundle_a_b",
                    scenario_id="E_bundle_cross_sell",
                    scope={
                        "type": "product_pair",
                        "id": f"{co['product_a']}+{co['product_b']}",
                        "products": [co["product_a"], co["product_b"]],
                    },
                    evidence=[
                        f"طلبات تحتوي المنتجين معًا: {co.get('orders_with_both')} من {co.get('orders_with_a')} طلبًا للمنتج A",
                        f"قوة الدليل: {co.get('evidence_strength')} (مبني على علاقة شراء محاكاة)",
                    ],
                    diagnosis="علاقة شراء تكميلية واضحة تدعم فرصة حزمة/بيع متقاطع.",
                    commercial_opportunity="عرض حزمة أو اقتراح متقاطع عند شراء A.",
                    recommended_action="اختبار اقتراح B عند شراء/سلة A لمدة 14 يومًا مع قياس معدل الحزمة والإيراد.",
                    why="الارتباط في سلة الشراء فعلي في المحاكاة وليس افتراض تصنيف.",
                    measurement_plan="معدل حزم A+B، AOV، إيراد الزوج — مقارنة بالأساس.",
                    recheck_condition="بعد 14 يومًا أو عند <5 حزم إضافية → inconclusiveness.",
                    confidence="medium",
                    status=MISSION_STATUS_PROPOSED,
                    falsifiers=[
                        "عينة تزامن ضعيفة → لا توصية حزمة.",
                        "ارتفاع الحزم مع انخفاض إيراد الزوج → أعد التصميم.",
                    ],
                )
            )

    # --- F Channel quality ---
    p07 = aggs.get("rrv_p07_channel") or {}
    ch = p07.get("channels") or {}
    tt = ch.get("tiktok") or {}
    gg = ch.get("google") or {}
    if (
        int(tt.get("views") or 0) >= MIN_CHANNEL_VIEWS
        and int(gg.get("views") or 0) >= MIN_CHANNEL_VIEWS
        and int(tt.get("atc") or 0) >= MIN_CHANNEL_ATC
        and float(tt.get("purchase_rate_of_atc") or 0) > float(gg.get("purchase_rate_of_atc") or 0) * 1.5
        and float(tt.get("aov") or 0) >= float(gg.get("aov") or 0) * 0.95
    ):
        out.append(
            _opp(
                opportunity_id="opp_f_channel_tiktok_vs_google_p07",
                scenario_id="F_channel_quality",
                scope={"type": "product", "id": "rrv_p07_channel", "name_ar": p07.get("name_ar")},
                evidence=[
                    f"TikTok: مشاهدات {tt.get('views')}، ATC {tt.get('atc')} ({tt.get('atc_rate'):.1%})، شراء/ATC {tt.get('purchase_rate_of_atc'):.1%}، AOV {tt.get('aov')}",
                    f"Google: مشاهدات {gg.get('views')}، ATC {gg.get('atc')} ({gg.get('atc_rate'):.1%})، شراء/ATC {gg.get('purchase_rate_of_atc'):.1%}، AOV {gg.get('aov')}",
                    "الفرق جودة قناة لهذا المنتج في المحاكاة فقط — ليس حكم فئة عامة",
                ],
                diagnosis="جودة اكتساب TikTok أعلى من Google لهذا المنتج ضمن العينة المحاكاة.",
                commercial_opportunity="تجربة اكتساب محدودة تعيد تخصيص جزء من الجهد نحو القناة الأعلى جودة لهذا المنتج.",
                recommended_action=(
                    "تجربة محدودة الميزانية/المدة على TikTok لهذا المنتج مع مجموعة مقارنة Google، "
                    "بدون توصية عامة «شغّل TikTok»."
                ),
                why="دليل القناة يشمل زيارات + ATC + شراء + AOV/إيراد — وليس حجم زيارات وحده.",
                measurement_plan="CPA/تكلفة إن وُجدت لاحقًا؛ هنا: ATC، شراء، AOV، إيراد لكل قناة.",
                recheck_condition="بعد 14 يومًا أو إذا انخفضت عينة أي قناة تحت العتبة → أوقف التوصية.",
                confidence="medium",
                status=MISSION_STATUS_PROPOSED,
                falsifiers=[
                    "عينة قناة صغيرة → لا إعادة تخصيص.",
                    "تقارب جودة القنوات → لا تجربة قناة.",
                    "ممنوع تعميم «TikTok أفضل للفئة».",
                ],
            )
        )

    # --- G Retention ---
    for seq in rel.get("retention_sequences") or []:
        if seq.get("materially_higher") and int(seq.get("buyers_of_first") or 0) >= MIN_RETENTION_BUYERS:
            out.append(
                _opp(
                    opportunity_id="opp_g_retention_a_to_b",
                    scenario_id="G_retention",
                    scope={
                        "type": "customer_segment",
                        "id": "buyers_of_rrv_p05_bundle_a",
                        "first_product": seq["first_product"],
                        "later_product": seq["later_product"],
                    },
                    evidence=[
                        f"مشترو A: {seq.get('buyers_of_first')}؛ اشتروا B لاحقًا: {seq.get('later_purchases')} ({seq.get('propensity'):.1%})",
                        f"خط أساس غير مشترين A: ~{seq.get('baseline_propensity_non_buyers'):.1%}",
                        "التصنيف: احتفاظ/بيع متقاطع لعملاء موجودين — ليس اكتسابًا",
                    ],
                    diagnosis="ميل لاحق أعلى ماديًا لدى مشترين A نحو B → فرصة احتفاظ موجّهة.",
                    commercial_opportunity="مهمة احتفاظ/cross-sell لعملاء A نحو B.",
                    recommended_action="حملة موجّهة لعملاء اشتروا A (رسالة/عرض تكميلي) لمدة 14 يومًا.",
                    why="العلاقة زمنية بعد الشراء وليست حملة اكتساب عامة.",
                    measurement_plan="معدل شراء B اللاحق، إيراد من الشريحة، بدون خلط مع زيارات جديدة.",
                    recheck_condition="بعد 21 يومًا؛ إذا لم يتجاوز الميل خط الأساس بفارق مادي → Lost/Inconclusive.",
                    confidence="medium",
                    status=MISSION_STATUS_PROPOSED,
                    falsifiers=[
                        "عدم فرق مادي عن الأساس → لا مهمة احتفاظ.",
                        "معاملة الشريحة كاكتساب → خطأ تصنيفي.",
                    ],
                )
            )

    # --- H Insufficient evidence ---
    p08 = aggs.get("rrv_p08_ambiguous") or {}
    if int(p08.get("views") or 0) < MIN_AMBIGUOUS_VIEWS_FOR_ACTION:
        out.append(
            _opp(
                opportunity_id="opp_h_insufficient_p08",
                scenario_id="H_insufficient_evidence",
                scope={"type": "product", "id": "rrv_p08_ambiguous", "name_ar": p08.get("name_ar")},
                evidence=[
                    f"مشاهدات منخفضة: {p08.get('views')} خلال {world.get('days')} يومًا",
                    f"ATC {p08.get('atc')}، مشتريات {p08.get('purchases')} — عينة غير كافية",
                    "تردّدات متقاربة (سعر/شحن/توصيل) بلا هيمنة واضحة",
                ],
                diagnosis="دليل غير كافٍ لأي إجراء تجاري. CartFlow يرفض التوصية.",
                commercial_opportunity="لا فرصة مؤهلة بعد.",
                recommended_action=(
                    "لا إجراء تجاري. المطلوب: مزيد من المشاهدات والإضافات، "
                    "وفصل أوضح لأسباب التردد عند توفرها."
                ),
                why="القانون: لا توصية بلا دليل. العينة والالتباس يمنعان التشخيص.",
                measurement_plan=(
                    f"جمع حتى ≥{MIN_AMBIGUOUS_VIEWS_FOR_ACTION} مشاهدة و≥{MIN_ATC_FOR_CONVERSION_DIAG} ATC "
                    "قبل إعادة النظر."
                ),
                recheck_condition=(
                    f"إعادة النظر تلقائيًا عند بلوغ {MIN_AMBIGUOUS_VIEWS_FOR_ACTION} مشاهدة "
                    "أو بعد دورة 30 يومًا إضافية."
                ),
                confidence="insufficient",
                status=MISSION_STATUS_INSUFFICIENT,
                falsifiers=[
                    "أي خصم/قناة/حزمة مقترحة الآن تُعد خرقًا للقانون.",
                ],
            )
        )

    # Demonstration statuses for UI: one measuring (won path), one active
    # Attach a measuring success example from steady product after a fictional bounded test window
    # Only if we already have a proposed C — clone status variant for review surfaces
    measuring = None
    for o in out:
        if o.get("scenario_id") == "C_price_sensitive" and o.get("status") == MISSION_STATUS_PROPOSED:
            measuring = dict(o)
            measuring["opportunity_id"] = "opp_c_price_experiment_p03_measuring"
            measuring["status"] = MISSION_STATUS_MEASURING
            measuring["evidence"] = list(o["evidence"]) + [
                "حالة القياس: التجربة بدأت؛ لم يُعلن رفع إيراد بعد — القياس جارٍ.",
            ]
            measuring["recommended_action"] = "الاستمرار في القياس حتى شرط الإيقاف/يوم 14 — بلا ادّعاء نتيجة مبكرة."
            break
    if measuring:
        out.append(measuring)

    # Successful measurement example (won) — only after measurement narrative, still simulation
    won = _opp(
        opportunity_id="opp_demo_measurement_won_p01",
        scenario_id="A_discovery",
        scope={"type": "product", "id": "rrv_p01_discovery", "name_ar": p01.get("name_ar")},
        evidence=[
            "بعد تجربة وضع أوضح في التصنيف لمدة 14 يومًا (محاكاة لاحقة):",
            "المشاهدات +52% مع ثبات ATC ضمن ±5%",
            "إيراد المنتج +31% مقابل الأساس — قياس مكتمل",
        ],
        diagnosis="تحسّن الاكتشاف المؤهل ثبت بالقياس.",
        commercial_opportunity="الإبقاء على الوضع الأقوى كافتراضي.",
        recommended_action="تثبيت التغيير ومراقبة 14 يومًا إضافية لأي تراجع.",
        why="النتيجة مقيسة على مشاهدات+ATC+إيراد — ليس انطباعًا.",
        measurement_plan="مراقبة استمرار الإيراد والمشاهدات أسبوعيًا.",
        recheck_condition="إذا انخفض الإيراد >15% لأسبوعين → إعادة فتح المهمة.",
        confidence="high",
        status=MISSION_STATUS_WON,
        falsifiers=["تراجع الإيراد مع ثبات المشاهدات → إعادة تشخيص جودة الزيارات."],
    )
    out.append(won)

    # One active mission example (channel experiment running)
    for o in out:
        if o.get("opportunity_id") == "opp_f_channel_tiktok_vs_google_p07":
            active = dict(o)
            active["opportunity_id"] = "opp_f_channel_active"
            active["status"] = MISSION_STATUS_ACTIVE
            active["evidence"] = list(o["evidence"]) + ["الحالة: التجربة النشطة قيد التنفيذ."]
            out.append(active)
            break

    return out


__all__ = ["detect_opportunities_v1"]
