# PIB-2 Implementation Review — Attention Truth & Decision Surface

**Document type:** Product Iteration implementation review  
**Status:** Complete — awaiting Product Review before PIB-3  
**Depends on:** PIB-1 APPROVED (`PIB_1_IMPLEMENTATION_REVIEW.md`)  
**Input contracts:** [`PRODUCT_REVIEW_SESSION_V1.md`](PRODUCT_REVIEW_SESSION_V1.md)  
**Evidence shape:** MV-1 (blocked contact wait + Knowledge phone-gap / demand)  
**Date (UTC):** 2026-07-17  

> **Mission:** Attention answers “What should I do first, and why?”  
> Attention is an ordered decision queue — never a passive list.

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| Home Attention decision contract (5 fields) | Home / Knowledge / Brief / Timeline redesign |
| Merchant priority ordering (blocked → immediate → passive) | AI / speculative priority |
| One operational decision → one Attention item | Authorities / MQIC / QTC changes |
| Merchant-visible if-ignored + expected outcome | PIB-3+ backlog items |
| Minimal presentation of new fields in existing Attention UI | Feature expansion |

**STOP:** Do not start PIB-3. Await Product Review.

---

## Attention Contract Verification

Every Attention item must contain:

| # | Required element | Field | Verification |
|---|------------------|-------|--------------|
| 1 | Clear merchant action | `action_ar` | Complete-or-drop gate; obtain-contact / fix-channel / contact-customer defaults from governed copy |
| 2 | Why this action is required | `why_ar` | From decision `why_now_ar` / Knowledge message — placeholders forbidden |
| 3 | Evidence supporting the action | `evidence_ar` | Case counts + Knowledge message (e.g. phone gap) |
| 4 | Current operational state | `operational_state_ar` | e.g. الاسترجاع متوقف — بانتظار رقم العميل (N حالات) |
| 5 | Expected outcome | `expected_outcome_ar` | What improves when merchant acts |
| + | If ignored (merchant acceptance) | `if_ignored_ar` | From `if_omitted_ar` / governed default |

Incomplete items (any of 1–5 missing or placeholder) are **not queued**.

`attention_today.decision_surface = true` marks the section as a decision queue. Lead copy states queue semantics.

---

## Priority Verification

| Rule | Implementation | Result |
|------|----------------|--------|
| Never visual / creation-time order | Sort by `priority_class` then case count / routing priority | **PASS** |
| Blocked merchant work first | `decision:obtain_contact` / `decision:fix_channel` → `priority_class = 0` | **PASS** |
| Immediate action before passive | `needs_attention` / suggested / critical with action → class `1`; else `2` | **PASS** |
| Attention never invents priority | Classes derived from operational decision + decision_class already published upstream | **PASS** |

MV-1 / mixed fixture: obtain-contact (blocked) precedes contact-customer (immediate).

---

## Knowledge Alignment

| Rule | Result |
|------|--------|
| Knowledge explains; Attention summarizes | Evidence/why enriched from KL `message_ar` when present |
| Attention does not invent priority | No new scoring engine; product class mapping only |
| Knowledge remains authority for explanation | Full insight set unchanged on Knowledge surface |
| Phone-gap health + obtain-contact = one decision | Both map to `operational_decision_key = decision:obtain_contact` |

---

## One Decision Verification

| Merchant problem | Attention item | Action | Evidence path |
|------------------|----------------|--------|---------------|
| Carts waiting for phone / store health “most carts without phone” | Single `decision:obtain_contact` | Obtain contact / open waiting carts | Case count + KL store-health message |

Duplicate operational decisions for the same phone-gap problem are forbidden and unit-tested.

---

## Engineering Verification

| Gate | Result | Evidence |
|------|--------|----------|
| No regressions | **PASS** | PIB-1 + Home experience + activation + dashboard UI tests green |
| Existing tests remain green | **PASS** | See commands below |
| Canonical truth unchanged | **PASS** | No Authority / MQIC / QTC / Decision-class / Knowledge minting changes |
| No duplicate decision source | **PASS** | Composition projects Brief + KL; merge by `operational_decision_key` only |

### Files changed

| File | Change |
|------|--------|
| `services/merchant_home_composition_v1.py` | Attention decision contract, merge, priority queue |
| `static/merchant_dashboard_home_v1.js` | Render state / evidence / outcome / if-ignored |
| `static/merchant_dashboard_home_v1.css` | Muted copy helpers (no redesign) |
| `static/merchant_home_experience.js` | PeV2 lead card shows decision fields |
| `tests/test_pib2_attention_decision_surface_v1.py` | **New** acceptance tests |

### Test commands

```text
python -m pytest tests/test_pib2_attention_decision_surface_v1.py tests/test_pib1_home_truth_alignment_v1.py tests/test_merchant_home_experience_v1.py tests/test_merchant_home_experience_activation_v1.py tests/test_dashboard_home_ui_v1.py -q
```

**Result:** All listed tests passed (2026-07-17).

---

## Product Verification

| Acceptance | Result |
|------------|--------|
| Every Attention item has a merchant purpose | **PASS** — incomplete items dropped |
| Priority ordering follows product contract | **PASS** — blocked before immediate/passive |
| Every action has supporting evidence | **PASS** — `evidence_ar` required |
| No duplicate operational decisions | **PASS** — one `operational_decision_key` per problem |
| No passive information blocks urgent work | **PASS** — priority_class ordering |

Maps to PRODUCT_REVIEW_SESSION_V1: C01, C07, HR-1, HR-9, and PIB-1 Attention truth preserved.

---

## Merchant Verification

A merchant opening Home must immediately know:

| Question | Home Attention answer | Status |
|----------|----------------------|--------|
| What requires action first? | Queue position `#1` / hero “أعلى أولوية اليوم” | **PASS** (unit MV-1 shape) |
| Why it requires action? | `why_ar` + `operational_state_ar` | **PASS** |
| What happens if ignored? | `if_ignored_ar` (hero + Attention card) | **PASS** |
| What to do next? | `action_ar` CTA | **PASS** |

**Merchant gate note:** Composition + UI field wiring verified. Attached Lab human retest remains part of overall product READY (PIB-12), not claimed here.

---

## Evidence

| Artifact | Role |
|----------|------|
| `PRODUCT_REVIEW_SESSION_V1.md` | Approved Attention contracts (D01 / C01 / C07) |
| `PIB_1_IMPLEMENTATION_REVIEW.md` | Home truth baseline (Attention non-empty, contact wait lead) |
| `tests/test_pib2_attention_decision_surface_v1.py` | Decision contract, merge, priority, UI tokens |

### Pre → Post (Attention)

| Aspect | After PIB-1 | After PIB-2 |
|--------|-------------|-------------|
| Contact wait present | Yes | Yes + full decision contract |
| Phone-gap + obtain-contact | Could be two Attention items | One `decision:obtain_contact` |
| Fields shown | headline / why / action | + state / evidence / outcome / if-ignored |
| Ordering | Contact first (heuristic) | Merchant priority classes (blocked → immediate → passive) |
| Incomplete items | Could surface thin cards | Dropped |

---

## Remaining Gaps

1. **Brief surface** still may list contact wait under achievements — Home corrects the decision queue; Brief≡Home is later backlog.  
2. **Timeline** not a decision surface — out of scope.  
3. **Attached human READY retest** (C15 / PIB-12) not claimed.  
4. **Generic informational Attention** without a governed action is dropped (by design); may reduce count vs raw Brief attention until those topics carry complete contracts upstream.

---

## Completion Gate

| Gate | Status |
|------|--------|
| 1. Engineering Acceptance | **PASS** |
| 2. Product Acceptance | **PASS** |
| 3. Merchant Acceptance | **PASS** on MV-1 composition + UI contract; attached human retest still required for full product READY |

**PIB-2 verdict:** Implementation complete for Attention Truth & Decision Surface.  

**STOP — await Product Review before opening PIB-3.**
