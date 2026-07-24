# Finding Decision Engine V1 — Production Proof

**Date (UTC):** 2026-07-24  
**Branch:** `feature/decision-engine-v1`  
**Flag:** `CARTFLOW_FINDING_DECISION_ENGINE_V1` (default ON)

## Objective

Convert every existing Business Finding into an actionable merchant Decision — or explicit **NO DECISION** when evidence is insufficient. No new Findings. No AI recommendations.

## Merchant leave-behind (Home)

Section **«ماذا تفعل اليوم؟»** paints first:

1. Decision  
2. Why  
3. Expected business impact  
4. Required merchant action  
5. Success metric  
6. Review window  
7. Decision confidence  
8. Evidence (traceable)

Insufficient evidence → **NO DECISION** + exact missing evidence under **«حيث لا يوجد قرار بعد»**.

## Wiring

| Layer | Artifact |
|-------|----------|
| Engine | `services/finding_decision_engine_v1.py` |
| Bind | MEBF `project_finding_render_contract_v1` → `merchant_decision_v1` |
| Home sections | `merchant_decisions` / `merchant_no_decisions` |
| Paint | `static/merchant_experience_integration_v1.js` (`applyHome`) |
| Tests | `tests/test_finding_decision_engine_v1.py` (10 passed) |

## Lab (historical SRS → BFL → Home)

Evidence: `docs/product/decision_engine_v1/lab_evidence.json`  
Examples: `docs/product/decision_engine_v1/decision_examples.json`

### Screenshots

| File | Content |
|------|---------|
| `docs/product/decision_engine_v1/03_desktop_home_decisions.png` | Desktop Home — decisions first |
| `docs/product/decision_engine_v1/04_mobile_home_decisions.png` | Mobile Home |
| `docs/product/decision_engine_v1/01_desktop_home_business_finding.png` | Full Home (findings context) |
| `docs/product/decision_engine_v1/02_mobile_home_business_finding.png` | Mobile full Home |

## Decision examples (from lab findings only)

### DECISION 1 — Widget contact capture

| Field | Value |
|-------|--------|
| Finding | `finding:recovery_channel_effectiveness_v1:widget` |
| Evidence | `reasons=18 contacts=0` |
| Decision | فعّل/حسّن طلب بيانات التواصل مباشرة بعد التقاط سبب التردد. |
| Why | 18 أسباب تردد بلا جهات اتصال قابلة للاسترجاع. |
| Impact | فتح مسار استرجاع لسلات كانت خارج التواصل. |
| Action | راجع إعداد الودجت لطلب رقم/تواصل صالح بعد السبب؛ راقب `contacts>0`. |
| Metric | `contacts > 0` مع استمرار `reasons≥1` |
| Review | 7 أيام |
| Confidence | medium |

### DECISION 2 — WhatsApp volume (do not scale)

| Field | Value |
|-------|--------|
| Finding | `finding:recovery_channel_effectiveness_v1:whatsapp` |
| Evidence | `sent=13 returned=0 purchased=0 failed=0 suppressed=0` |
| Decision | لا توسّع حجم رسائل واتساب للاسترجاع هذا الأسبوع. |
| Why | 13 رسالة بلا عودة/شراء موثّق — التوسيع قبل الأثر تخمين. |
| Impact | تجنّب تكلفة/ضجيج بلا عائد ظاهر. |
| Action | ثبّت الحجم؛ لا ترفع الإرسال حتى `returned≥1` أو `purchased≥1`. |
| Metric | `returned≥1` أو `purchased≥1` على الدفعات الجديدة |
| Review | 7 أيام |
| Confidence | medium |

### NO DECISION 1 — Traffic vs conversion

| Field | Value |
|-------|--------|
| Finding | `finding:traffic_versus_conversion_v1` |
| Evidence present | `visitor_total=unavailable; carts_not_used_as_traffic_proxy` |
| Missing | ثقة الاستنتاج غير كافية (`confidence=insufficient`) — مطلوب أدلة أقوى على نفس النمط. |
| Status | **NO DECISION** |

### NO DECISION 2 — Dominant hesitation (not dominant)

| Field | Value |
|-------|--------|
| Finding | `finding:dominant_hesitation_reason_v1:not_dominant` |
| Evidence present | `top=delivery:4/18 share=22%` |
| Missing | سبب مهيمن بحصة كافية عبر أيام إضافية (الحصة الحالية غير كافية لقرار تغيير العرض). |
| Status | **NO DECISION** |

## Final assessment

**Would a merchant execute these decisions this week?**

**Yes — for the two DECISION items.** They are concrete (widget contact after reason; hold WhatsApp volume), evidence-bound (`reasons=18 contacts=0`, `sent=13 returned=0 purchased=0`), with a 7-day metric the merchant can check without guessing.

**No — for the two NO DECISION items.** The engine correctly refuses traffic and non-dominant hesitation until visitor truth / stronger share exists. That refusal is the product: merchants are not asked to act on insufficient evidence.

Overall merchant Home experience: leave knowing **what to do today** (2 actions), **why**, and **how success is measured** — and where CartFlow will not invent a decision.
