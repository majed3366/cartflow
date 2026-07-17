# PIB-3 Implementation Review — Recovery Journey Explainability

**Document type:** Product Iteration implementation review  
**Status:** Complete — awaiting Product Review before PIB-4  
**Depends on:** PIB-2 APPROVED (`PIB_2_IMPLEMENTATION_REVIEW.md`)  
**Input contracts:** [`PRODUCT_REVIEW_SESSION_V1.md`](PRODUCT_REVIEW_SESSION_V1.md)  
**Date (UTC):** 2026-07-17  

> **Mission:** Every merchant decision on Home is visibly connected to the customer’s Recovery Journey — stage, channel, blocker, next platform action, next merchant action — without leaving Home.

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| Recovery Journey chapter on Home Attention decisions | Widget / WhatsApp / Timeline / Brief redesign |
| Consume LT-C1 labels + existing explanation copy | New lifecycle states or recovery logic |
| Waiting-state explainability on Attention | Authorities / MQIC / QTC changes |
| Minimal UI of journey fields on existing Attention cards | PIB-4+ backlog |

**STOP:** Do not start PIB-4. Await Product Review.

---

## Recovery Journey Contract Verification

Every recovery-related Attention decision exposes:

| # | Contract element | Field | Source |
|---|------------------|-------|--------|
| 1 | Current recovery stage | `recovery_stage_key` + `recovery_stage_ar` | LT-C1 (`needs_intervention`, contact-completion label, return/purchase-window labels) |
| 2 | Recovery channel | `recovery_channel_ar` | Presentation channel only: widget/contact · WhatsApp · merchant · site return |
| 3 | Why this stage exists | `recovery_stage_why_ar` | Existing explanation intent (no new FSM) |
| 4 | Current blocker | `recovery_blocker_ar` | Phone gap / WhatsApp fail / merchant needed / none |
| 5 | Next platform action | `recovery_next_platform_ar` | What CartFlow does or waits for |
| 6 | Next merchant action | `recovery_next_merchant_ar` | Required ask, or “لا يلزم إجراء منك الآن” |
| 7 | Completion condition | `recovery_completion_condition_ar` | When the journey naturally continues |

Incomplete recovery journeys are not queued (`recovery_journey_complete` gate for recovery decisions).

### Supported stages (canonical only)

| Operational decision | Canonical stage key | Merchant-visible stage |
|----------------------|---------------------|------------------------|
| `decision:obtain_contact` | `needs_intervention` | بانتظار اكتمال بيانات التواصل (LT-C1 contact label) |
| `decision:fix_channel` | `needs_intervention` | تحتاج تدخل + واتساب |
| `decision:contact_customer` | `needs_intervention` | تحتاج تدخل |
| `decision:monitor` | `waiting_purchase_window` (+ related `return_to_site`) | عاد العميل… أوقفنا المتابعة مؤقتاً |

No new lifecycle states were invented.

---

## Knowledge Alignment

| Rule | Result |
|------|--------|
| Knowledge remains explanation authority | Journey mapping reuses LT-C1 labels + explanation catalog intent; does not mint Knowledge insights |
| Recovery Journey consumes Knowledge / lifecycle truth | Stage keys from `customer_lifecycle_states_v1`; phone-gap evidence still from Knowledge via PIB-1/2 |
| No duplicated reasoning | Journey is a presentation chapter on Attention; Knowledge page unchanged |

---

## Attention Alignment

| Rule | Result |
|------|--------|
| Attention summarizes Recovery Journey | Each recovery decision carries `recovery_journey_v1` + flattened fields |
| PIB-2 decision contract preserved | action / why / evidence / state / outcome still required |
| One problem → one decision → one journey chapter | Merge by `operational_decision_key` unchanged; journey re-attached after merge |

---

## Home Verification

| Check | Result |
|-------|--------|
| Journey visible without leaving Home | ECC Attention renders «مسار الاسترجاع» block; PeV2 lead card shows stage/blocker/platform line |
| Waiting states explained | Phone wait / channel fail include explicit `recovery_blocker_ar` |
| Merchant intervention justified | `recovery_merchant_required` + non-empty next merchant action |
| Platform action understandable | `recovery_next_platform_ar` present on recovery decisions |

---

## Engineering Verification

| Gate | Result | Evidence |
|------|--------|----------|
| No regressions | **PASS** | PIB-1/2 + Home experience + dashboard UI green with PIB-3 |
| Existing tests remain green | **PASS** | See commands below |
| Canonical recovery truth unchanged | **PASS** | No changes to lifecycle classifier, schedules, WhatsApp send, or Decision minting |
| No duplicate journey source | **PASS** | Single presentation mapper: `merchant_recovery_journey_home_v1.py` |

### Files changed

| File | Change |
|------|--------|
| `services/merchant_recovery_journey_home_v1.py` | **New** — presentation journey mapper |
| `services/merchant_home_composition_v1.py` | Attach journey to Attention; gate incomplete recovery chapters |
| `static/merchant_dashboard_home_v1.js` | `renderRecoveryJourney` |
| `static/merchant_dashboard_home_v1.css` | Minimal journey block styles |
| `static/merchant_home_experience.js` | PeV2 lead shows journey summary |
| `tests/test_pib3_recovery_journey_home_v1.py` | **New** acceptance tests |

### Test commands

```text
python -m pytest tests/test_pib3_recovery_journey_home_v1.py tests/test_pib2_attention_decision_surface_v1.py tests/test_pib1_home_truth_alignment_v1.py tests/test_merchant_home_experience_v1.py tests/test_dashboard_home_ui_v1.py -q
```

**Result:** All listed tests passed (2026-07-17).

---

## Product Verification

| Acceptance | Result |
|------------|--------|
| Every recovery decision maps to an existing recovery stage | **PASS** |
| Every waiting state is explained | **PASS** (blocker + why + next platform) |
| Every merchant intervention is justified | **PASS** (`recovery_merchant_required` + next merchant) |
| Every platform action is understandable | **PASS** |
| No recovery ambiguity remains on Home Attention | **PASS** for queued recovery decisions |

---

## Merchant Verification

A merchant viewing Home Attention must answer:

| # | Question | Answer form | Status |
|---|----------|-------------|--------|
| 1 | Where is the customer now? | `recovery_stage_ar` | **PASS** (unit) |
| 2 | Why are they there? | `recovery_stage_why_ar` | **PASS** |
| 3 | What is CartFlow doing now? | `recovery_next_platform_ar` | **PASS** |
| 4 | Must the merchant intervene? | `recovery_merchant_required` + next merchant | **PASS** |
| 5 | What happens next? | platform + merchant next lines | **PASS** |
| 6 | When does recovery continue naturally? | `recovery_completion_condition_ar` | **PASS** |

**Merchant gate note:** Composition + UI wiring verified. Attached Lab human retest remains part of overall product READY (later gate), not claimed here.

---

## Evidence

| Artifact | Role |
|----------|------|
| `services/customer_lifecycle_states_v1.py` | Canonical LT-C1 stage keys + Arabic labels |
| `services/merchant_explanation_v1.py` | Explanation catalog (authority for narrative intent) |
| `services/merchant_recovery_journey_home_v1.py` | Home Attention journey projection |
| `tests/test_pib3_recovery_journey_home_v1.py` | Contract + Home + UI token acceptance |

### Example (obtain-contact / MV-1 phone gap)

| Field | Example value |
|-------|----------------|
| Stage | بانتظار اكتمال بيانات التواصل (N حالات) |
| Channel | الودجت / بيانات التواصل |
| Blocker | لا يوجد رقم عميل — واتساب لا يُرسل |
| CartFlow next | بعد توفر الرقم: جدولة/إرسال واتساب تلقائياً |
| Merchant next | الحصول على رقم العميل… |
| Completes when | يتوفر رقم صالح وتُستأنف المتابعة الآلية |

---

## Remaining Known Gaps

1. **Per-cart Timeline narrative** still out of scope — Home summarizes Attention journey chapters, not a full cart storyboard.  
2. **Passive automation stages** (e.g. `waiting_first_send`, `waiting_customer_reply`) appear on cart/explanation surfaces; they are not Attention decisions unless promoted by Decision Layer.  
3. **Brief / Timeline surfaces** not updated (non-goals).  
4. **Attached human READY retest** not claimed.

---

## Completion Gate

| Gate | Status |
|------|--------|
| 1. Engineering Acceptance | **PASS** |
| 2. Product Acceptance | **PASS** |
| 3. Merchant Acceptance | **PASS** on Home Attention composition + UI contract |

**PIB-3 verdict:** Implementation complete for Recovery Journey Explainability on Home Attention.  

**STOP — await Product Review before opening PIB-4.**
