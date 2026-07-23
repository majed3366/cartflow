# Commercial Question Registry V1

**Status:** Production foundation  
**Success metric (official):** Home is measured by *the number of different commercial questions CartFlow can answer with evidence* — not cards, carts, events, or widgets.

---

## 1. Purpose

CartFlow Home must answer **WHY / WHAT / SO WHAT / WHAT NEXT** — not operational reporting.

Every Home insight must answer exactly one registered commercial question.

---

## 2. Admission rule

Home admits an insight **only if** it answers a commercial question and carries:

1. Commercial Question  
2. Commercial Answer  
3. Evidence  
4. Confidence  
5. Merchant Meaning  
6. Recommended Action *(when appropriate; insufficient evidence may omit action)*

**Forbidden:** counts, events, timelines, or operational status unless they directly support a commercial conclusion.

**Insufficient evidence** is valuable and may be admitted when the question allows it.

---

## 3. Registry (runtime)

Canonical implementation: `services/commercial_question_registry_v1.py`

| ID | Dimension | Question (AR) |
|----|-----------|----------------|
| CQ-P01 | products | أي منتجات تجذب الانتباه لكنها تفشل في التحويل؟ |
| CQ-P02 | products | أي منتجات تدخل السلة مراراً دون شراء؟ |
| CQ-P03 | products | أي منتجات تولّد تردداً أو اهتماماً ضعيفاً؟ |
| CQ-H01 | hesitation | ما أكثر سبب يسبب تردد العملاء؟ |
| CQ-H02 | hesitation | هل أصبحت تكلفة الشحن العائق الأبرز؟ |
| CQ-H03 | hesitation | هل الأسعار تدفع للتخلي عن الشراء؟ |
| CQ-H04 | hesitation | هل يعالج الاسترجاع أسباب التردد فعلاً؟ |
| CQ-T01 | traffic | هل لدينا أدلة كافية لتقييم جودة الزيارات؟ |
| CQ-T02 | traffic | هل الزيارات تتحسّن أم تصبح أكثر تأهيلاً؟ |
| CQ-R01 | recovery | أي مسار استرجاع يغيّر النتائج فعلاً؟ |
| CQ-R02 | recovery | هل قناة الاسترجاع ترفع المشتريات أم العودة فقط؟ |
| CQ-W01 | whatsapp | هل توقيت رسالة واتساب يستحق اختباراً تجارياً؟ |
| CQ-G01 | merchant_guidance | أي قضية تستحق الانتباه أولاً؟ |
| CQ-G02 | merchant_guidance | أي قضية أدلتها ضعيفة؟ |
| CQ-K01 | knowledge | ماذا تعلّم CartFlow مؤخراً عن المتجر؟ |
| CQ-K02 | knowledge | أي استنتاجات أصبحت أقوى أو أضعف؟ |
| CQ-D01 | missing_evidence | ماذا ما زلنا لا نعرف — وأين نحتاج أدلة؟ |
| CQ-C01 | contact | هل نقص بيانات التواصل يعيق استرجاع الإيراد؟ |

The registry **must grow** with the platform (`growth: true` on all entries).

---

## 4. Question → Insight → Home slot mapping

| Question family | Finding type(s) | Home section |
|-----------------|-----------------|--------------|
| CQ-P* | high_interest_low_purchase / repeated_interest / low_interest | Understanding / Opportunity |
| CQ-H* | dominant_hesitation / hesitation_resolution | Understanding / Learning |
| CQ-T* | traffic_versus_conversion | Understanding / Learning (often insufficient) |
| CQ-R* | return_without_purchase / channel_effectiveness | Understanding / Opportunity |
| CQ-W* | whatsapp_message_timing_test | Opportunity / Learning |
| CQ-D* / CQ-K* | insufficient_or_conflicting / meta | Learning |
| CQ-C01 | missing_contact (+ CIL) | Priority / Health condition |
| CQ-G01 | act_now priority among findings | Priority |

Engine: `services/home_commercial_intelligence_v1.py`  
Diversity rule: at most one visible insight per commercial dimension; contact must not monopolize Understanding/Opportunity/Learning.

---

## 5. Evidence generation flow

```
Truth / EvidenceBundle (DB or demo fixture)
  → Business Findings Engine (deterministic families)
  → Commercial Question Registry mapping
  → Commercial insight (Q→A→Evidence→Confidence→Meaning→Action)
  → Home section projection (existing cards only)
  → Semantic composition (dedupe paraphrases)
  → Adaptive Cognition section_order (admitted only)
  → JS presentation
```

No AI-generated conclusions.

---

## 6. Files

| Artifact | Path |
|----------|------|
| Registry runtime | `services/commercial_question_registry_v1.py` |
| Home admission | `services/home_commercial_intelligence_v1.py` |
| Wire-in | `merchant_home_composition_v1.finalize_home_daily_business_brief_v1` |
| Validation | `HOME_COMMERCIAL_INTELLIGENCE_TRANSITION_V1_VALIDATION.md` |

---

## STOP

Await Product Review. No new pages. No Home redesign. No AI conclusions.
