# PIB-1 Implementation Review — Home Truth Alignment

**Document type:** Product Iteration implementation review  
**Status:** Complete — awaiting Product Review before PIB-2  
**Input contracts:** [`PRODUCT_REVIEW_SESSION_V1.md`](PRODUCT_REVIEW_SESSION_V1.md)  
**Evidence shape:** MV-1 (5 carts without phone, demand 5→0, Knowledge insights present)  
**Date (UTC):** 2026-07-17  

> **Mission:** Make Home the shortest truthful explanation of current store state.  
> Home must never contradict Knowledge. Home must never hide important merchant action.

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| Home Attention truth | PIB-2+ backlog items as separate work packages |
| Home Understanding inheritance from Knowledge | Daily Brief surface redesign (PIB-7) |
| One fact → one Home card | Timeline narrative rewrite (PIB-8 / PIB-9) |
| Ban placeholder Home card detail | UI redesign / section reorder |
| Home active-carts badge = Knowledge `cart_count` | Authorities / MQIC / QTC changes |
| Greeting date fallback to `brief_date` | New product concepts / new cards |

**STOP:** Do not start PIB-2. Await Product Review.

---

## Implemented Product Contracts

| Contract | Source | Implementation |
|----------|--------|----------------|
| Contact wait / blocked recovery → Attention #1 | MV1-D01, C01, HR-1 | Home promotes `obtain_contact` from Brief achievements into `attention_today` and sorts it first |
| Never calm-empty Attention when contact wait exists | MV1-D01, HR-2 | Attention `count ≥ 1` whenever blocked contact fact exists |
| Attention states next step | MV1-D01, C07, HR-9 | Contact-wait / phone-gap items get action: الحصول على رقم العميل… |
| Understanding inherits Knowledge messages/numbers | MV1-D02, D12, C02, HR-3 | KL insights eligible for `merchant_home`; Home routes demand + store health into `store_understanding` |
| Never claim “no understanding” when Knowledge has evidence | MV1-D02, HR-4 | Understanding non-empty when KL has merchant-usable insights |
| One fact → one card | MV1-D03, HR-5 | Cross-section `fact_key` dedupe (Attention / Understanding / While-away) |
| No placeholder why/detail | MV1-D04, HR-6 | Drop or replace «ملخص Knowledge Layer…» / «—»; enrich from Knowledge `message_ar` when available |
| Badge = Knowledge `cart_count` | MV1-D05, HR-7 | Live Home sets `nav.knowledge_cart_count` from Knowledge metrics; quick-nav badge uses it |
| Insufficient / unavailable not while-away wins | MV1-D09, C10 | Limit insights filtered out of Home while-away |
| Greeting date equals brief day when header empty | MV1-D08, HR-8 | `date_ar` falls back to `brief_date` |
| Home summarizes Knowledge (does not replace it) | Product contract | Home shows capped Attention/Understanding slices; full insight set remains on Knowledge |

---

## Engineering Verification

| Gate | Result | Evidence |
|------|--------|----------|
| No regressions in Home / routing / activation / identity consumers | **PASS** | `tests/test_pib1_home_truth_alignment_v1.py` + adjacent suites green |
| Existing Home experience tests remain green | **PASS** | `tests/test_merchant_home_experience_v1.py` |
| Activation / snapshot attach still attaches Home | **PASS** | `tests/test_merchant_home_experience_activation_v1.py` (fixture updated to non-placeholder why) |
| KL → `merchant_home` eligibility | **PASS** | `tests/test_knowledge_routing_v1.py::test_merchant_home_surface_routing` asserts `eligible_items ≥ 1` |
| Canonical truth unchanged | **PASS** | No changes to Authorities, MQIC, QTC, Knowledge metrics/insight minting, or Decision class capping |
| No duplicated truth source | **PASS** | Home still consumes Brief + Knowledge report; composition only projects |
| No performance regression (composition path) | **PASS** | Same upstream calls; no new hot-path DB queries beyond existing Home Knowledge report |

### Files changed

| File | Change |
|------|--------|
| `services/merchant_home_composition_v1.py` | Home truth alignment composition (Attention promote, Understanding inherit, dedupe, placeholders, badge, date) |
| `services/knowledge_producer_metadata_v1.py` | Add `merchant_home` to KL `eligible_surfaces` |
| `services/merchant_home_experience_activation_v1.py` | Pass summary KL insights + Knowledge cart_count when present |
| `tests/test_pib1_home_truth_alignment_v1.py` | **New** — C01/C02/C03/C04/C05/C06/C07/C10 acceptance |
| `tests/test_knowledge_producer_metadata_v1.py` | Assert `merchant_home` surface |
| `tests/test_knowledge_routing_v1.py` | Assert Home routing eligibility |
| `tests/test_merchant_home_experience_activation_v1.py` | Non-placeholder achievement fixture |

### Test commands

```text
python -m pytest tests/test_pib1_home_truth_alignment_v1.py tests/test_merchant_home_experience_v1.py tests/test_merchant_home_experience_activation_v1.py -q
python -m pytest tests/test_knowledge_routing_v1.py tests/test_knowledge_producer_metadata_v1.py tests/test_dashboard_home_ui_v1.py tests/identity_authority/test_wp5_dashboard_home_consumer.py tests/identity_authority/test_wp6_timeline_consumer.py -q
```

**Result:** All listed tests passed in local run (2026-07-17).

---

## Product Verification

| Checklist | Result | Notes |
|-----------|--------|-------|
| C01 Attention tells the truth | **PASS** (unit MV-1 shape) | Contact wait in Attention; not calm-empty |
| C02 Understanding tells the truth | **PASS** (unit MV-1 shape) | Demand / health numbers from Knowledge |
| C03 No duplicate spam on Home | **PASS** (unit) | Fact keys unique across Home sections |
| C04 No placeholder why | **PASS** (unit) | Placeholders removed / enriched |
| C05 Cart chrome matches store | **PASS** (unit) | Badge = Knowledge cart_count (5) |
| C06 Dated today | **PASS** (unit) | Greeting date = brief_date when header empty |
| C07 Next step exists | **PASS** (unit) | Attention #1 = obtain_contact with action |
| C08–C12 Brief / Timeline | **OUT OF SCOPE** | PIB-7 / PIB-8 / PIB-9 |
| C13 Knowledge still honest | **PASS** | Knowledge producer/decision truth not modified |
| C14 Cross-surface counts | **PARTIAL** | Home badge aligned to Knowledge; Brief surface not changed this PIB |
| C15 Trust sentence | **PENDING** | Requires attached MV-1 retest + human reviewer |

Every implemented Home behavior maps to PRODUCT_REVIEW_SESSION_V1. No new cards or speculative UI.

---

## Merchant Verification

First-time merchant questions answered from Home after this change (MV-1 evidence shape, unit-verified):

| # | Merchant question | Home answer form | Status |
|---|-------------------|------------------|--------|
| 1 | What is happening now? | Dated greeting (`brief_date`) + Understanding demand direction | **PASS** (unit) |
| 2 | What needs attention now? | Attention #1 = contact wait (5 cases) | **PASS** (unit) |
| 3 | Why does it need attention? | Why line with phone-gap / recovery-block evidence | **PASS** (unit) |
| 4 | What evidence supports it? | Counts in Attention why + Understanding observation (5 vs 0 / بدون رقم) | **PASS** (unit) |
| 5 | What action should be taken? | Attention action: obtain customer contact / open waiting carts | **PASS** (unit) |

**Merchant gate note:** Unit composition proves the speech contract. Final merchant confidence still requires attached Lab session retest (PRODUCT_REVIEW_SESSION_V1 READY path / PIB-12). That retest is **not** claimed complete here.

---

## Evidence

| Artifact | Role |
|----------|------|
| `PRODUCT_REVIEW_SESSION_V1.md` | Approved product contracts |
| `docs/architecture/merchant_reality_validation_v1/mv1_home_sections.json` | Pre-fix Home empty Attention/Understanding + badge 0 |
| `docs/architecture/merchant_reality_validation_v1/mv1_session_capture.json` | Pre-fix while-away dump + Knowledge cart_count=5 |
| `tests/test_pib1_home_truth_alignment_v1.py` | Post-fix Home speech acceptance on MV-1 shape |

### Pre → Post (composition intent)

| Surface field (MV-1 shape) | Before | After (PIB-1) |
|----------------------------|--------|---------------|
| `attention_today.count` | 0 | ≥ 1 (contact wait lead) |
| Attention empty calm copy shown | Yes | No (items present) |
| `store_understanding.items` | [] | ≥ 1 (demand and/or health) |
| Placeholder «ملخص…» / «—» on Home cards | Present | Absent |
| Active-carts `badge_count` | 0 | 5 (= Knowledge `cart_count`) |
| Contact wait in while-away as win | Yes | No (moved to Attention) |

---

## Remaining Known Gaps

1. **Brief still misclassifies contact wait as achievement** — Home corrects presentation; Brief surface consistency is PIB-7.  
2. **Timeline still mirrors achievement dump** — narrative + evidence beats are PIB-8 / PIB-9.  
3. **Snapshot/degraded Home without embedded KL insights** — Understanding may stay empty if summary lacks Knowledge payload (live/attach path builds Knowledge).  
4. **C15 trust sentence** — not claimed; needs human attached-session READY retest (PIB-12).  
5. **Store display name** — still may show «متجرك» (P3 / PIB-11; not required for this gate).

---

## Completion Gate

| Gate | Status |
|------|--------|
| 1. Engineering Acceptance | **PASS** |
| 2. Product Acceptance (Home contracts in this PIB) | **PASS** (unit + contract mapping); full C01–C15 product READY remains blocked on Brief/Timeline/PIB-12 |
| 3. Merchant Acceptance (five questions from Home) | **PASS** on MV-1 composition shape; attached human retest still required for product READY |

**PIB-1 verdict:** Implementation complete for Home Truth Alignment.  
**Product READY (C01–C15):** Not claimed — remaining backlog items and READY retest still open.

**STOP — await Product Review before opening PIB-2.**
